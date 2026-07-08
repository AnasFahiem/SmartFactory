using MQTTnet;
using MQTTnet.Client;
using Microsoft.AspNetCore.SignalR;
using IoTBackend.Hubs;
using IoTBackend.Data;
using IoTBackend.Models;
using Microsoft.EntityFrameworkCore;
using System.Globalization;
using System.Text;
using System.Text.Json;

namespace IoTBackend.Services;

public class MqttService : BackgroundService
{
    private readonly IMqttClient _mqttClient;
    private readonly IHubContext<FactoryHub> _hubContext;
    private readonly IServiceScopeFactory _scopeFactory;
    private readonly ILogger<MqttService> _logger;
    private readonly IConfiguration _configuration;

    private CancellationTokenSource? _weightRequestCts;
    private string? _lastReceivedQr;
    private string CommandTopic => _configuration["Mqtt:CommandTopic"] ?? "factory/commands";

    public MqttService(IMqttClient mqttClient, IHubContext<FactoryHub> hubContext,
                       IServiceScopeFactory scopeFactory, ILogger<MqttService> logger,
                       IConfiguration configuration)
    {
        _mqttClient = mqttClient;
        _hubContext = hubContext;
        _scopeFactory = scopeFactory;
        _logger = logger;
        _configuration = configuration;
    }

    public async Task RequestWeightAsync()
    {
        if (_mqttClient != null && _mqttClient.IsConnected)
        {
            var message = new MqttApplicationMessageBuilder()
                .WithTopic(CommandTopic)
                .WithPayload("GET_WEIGHT") 
                .WithQualityOfServiceLevel(MQTTnet.Protocol.MqttQualityOfServiceLevel.AtLeastOnce)
                .Build();

            await _mqttClient.PublishAsync(message);
            _logger.LogInformation($"Sent GET_WEIGHT command to ESP32 on {CommandTopic}.");
        }
        else
        {
            _logger.LogWarning("Cannot request weight: MQTT Client is not connected.");
        }
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        var mqttConfig = _configuration.GetSection("Mqtt");
        var mqttHost = mqttConfig["Host"];
        if (string.IsNullOrWhiteSpace(mqttHost))
        {
            _logger.LogWarning("MQTT is disabled because Mqtt:Host is not configured.");
            return;
        }

        var mqttPort = int.TryParse(mqttConfig["Port"], out var configuredPort) ? configuredPort : 8883;
        var mqttClientId = mqttConfig["ClientId"] ?? "IoTBackend";
        var mqttUsername = mqttConfig["Username"];
        var mqttPassword = mqttConfig["Password"];
        var useTls = bool.TryParse(mqttConfig["UseTls"], out var configuredUseTls) ? configuredUseTls : true;
        var topics = mqttConfig.GetSection("Topics")
            .GetChildren()
            .Select(topic => topic.Value)
            .Where(topic => !string.IsNullOrWhiteSpace(topic))
            .Cast<string>()
            .Distinct()
            .ToArray();
        if (topics.Length == 0)
        {
            topics = new[] { "factory/#" };
        }

        var optionsBuilder = new MqttClientOptionsBuilder()
            .WithClientId(mqttClientId)
            .WithTcpServer(mqttHost, mqttPort)
            .WithCleanSession();

        if (!string.IsNullOrWhiteSpace(mqttUsername))
        {
            optionsBuilder.WithCredentials(mqttUsername, mqttPassword);
        }

        if (useTls)
        {
            optionsBuilder.WithTlsOptions(o =>
            {
                o.UseTls();
                o.WithSslProtocols(System.Security.Authentication.SslProtocols.Tls12);
            });
        }

        var options = optionsBuilder.Build();

        _mqttClient.ApplicationMessageReceivedAsync += HandleMessageAsync;

        _ = Task.Run(async () =>
        {
            while (!stoppingToken.IsCancellationRequested)
            {
                try
                {
                    if (!_mqttClient.IsConnected)
                    {
                        await _mqttClient.ConnectAsync(options, stoppingToken);
                        foreach (var topic in topics)
                        {
                            await _mqttClient.SubscribeAsync(topic);
                        }
                        _logger.LogInformation($"MQTT Connected and subscribed to: {string.Join(", ", topics)}");
                    }
                }
                catch (Exception ex)
                {
                    _logger.LogError($"MQTT Connection failed: {ex.Message}");
                }
                await Task.Delay(5000, stoppingToken); 
            }
        }, stoppingToken);

        await Task.Delay(Timeout.Infinite, stoppingToken);
    }

    private async Task HandleMessageAsync(MqttApplicationMessageReceivedEventArgs e)
    {
        var payload = Encoding.UTF8.GetString(e.ApplicationMessage.PayloadSegment);
        var topic = e.ApplicationMessage.Topic;

        _logger.LogInformation($"Received: {topic} -> {payload}");

        if (string.IsNullOrWhiteSpace(payload))
        {
            return;
        }

        if (topic.Equals(CommandTopic, StringComparison.OrdinalIgnoreCase))
        {
            return;
        }

        JsonDocument? doc = null;

        try
        {
            JsonElement? root = null;
            try
            {
                doc = JsonDocument.Parse(payload);
                root = doc.RootElement;
            }
            catch (JsonException)
            {
                // Some ESP32 messages are plain payloads published to topic-specific
                // channels, e.g. topic factory/qr with payload "P-1001".
            }

            if (TryExtractQrValue(topic, payload, root, out var qrValue))
            {
                await HandleQrAsync(qrValue);
            }

            if (TryExtractDouble("temperature", topic, payload, root, out var temp))
                await _hubContext.Clients.All.SendAsync("ReceiveTemperatureUpdate", temp);

            if (TryExtractDouble("humidity", topic, payload, root, out var hum))
                await _hubContext.Clients.All.SendAsync("ReceiveHumidityUpdate", hum);

            if (TryExtractDouble("weight", topic, payload, root, out var weight))
            {
                await HandleWeightAsync(weight);
            }

            if (TryExtractBool("gas_alarm", topic, payload, root, out var gasAlarm))
            {
                await _hubContext.Clients.All.SendAsync("ReceiveSmokeUpdate", gasAlarm);
            }

            if (root.HasValue &&
                root.Value.ValueKind == JsonValueKind.Object &&
                root.Value.TryGetProperty("ai_alert", out var aiAlert) &&
                aiAlert.ValueKind == JsonValueKind.True)
            {
                string msgText = root.Value.TryGetProperty("message", out var msgNode) ? msgNode.GetString() : "AI Anomaly Detected!";
                await _hubContext.Clients.All.SendAsync("ReceiveAiAlert", msgText);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error parsing MQTT JSON: {ex.Message}");
        }
        finally
        {
            doc?.Dispose();
        }
    }

    private async Task HandleQrAsync(string qrValue)
    {
        _lastReceivedQr = qrValue;

        await _hubContext.Clients.All.SendAsync("ReceiveProductNumberUpdate", qrValue);
        _logger.LogInformation($"QR Code forwarded to SignalR clients: {qrValue}");

        _weightRequestCts?.Cancel();
        _weightRequestCts = new CancellationTokenSource();
        var token = _weightRequestCts.Token;

        _ = Task.Run(async () =>
        {
            var requestIntervalSeconds = Math.Max(
                1,
                _configuration.GetValue<int?>("Mqtt:WeightRequestIntervalSeconds") ?? 6);

            try
            {
                while (!token.IsCancellationRequested)
                {
                    await RequestWeightAsync();
                    await Task.Delay(TimeSpan.FromSeconds(requestIntervalSeconds), token);
                }
            }
            catch (TaskCanceledException)
            {
            }
        }, token);
    }

    private async Task HandleWeightAsync(double actualWeight)
    {
        _weightRequestCts?.Cancel();
        _logger.LogInformation("Weight received. Stopped sending requests.");

        await _hubContext.Clients.All.SendAsync("ReceiveWeightUpdate", actualWeight);

        if (string.IsNullOrWhiteSpace(_lastReceivedQr))
        {
            return;
        }

        using var scope = _scopeFactory.CreateScope();
        var dbContext = scope.ServiceProvider.GetRequiredService<AppDbContext>();
        var product = await dbContext.Products.FirstOrDefaultAsync(p => p.ProductNumber == _lastReceivedQr);
        if (product == null)
        {
            _logger.LogWarning($"No product found for scanned QR value: {_lastReceivedQr}");
            return;
        }

        dbContext.ProductScans.Add(new ProductScan
        {
            ProductNumber = _lastReceivedQr,
            ActualWeight = (decimal)actualWeight,
            ScanTime = DateTime.UtcNow
        });
        await dbContext.SaveChangesAsync();
        _logger.LogInformation($"Saved actual weight {actualWeight} for product {_lastReceivedQr}");

        if (!product.Weight.HasValue)
        {
            return;
        }

        decimal idealWeight = product.Weight.Value;
        decimal tenPercent = idealWeight * 0.10m;
        bool isWithin10Percent = Math.Abs((decimal)actualWeight - idealWeight) <= tenPercent;

        string commandPayload = isWithin10Percent ? "true" : "false";
        var msg = new MqttApplicationMessageBuilder()
            .WithTopic(CommandTopic)
            .WithPayload(commandPayload)
            .WithQualityOfServiceLevel(MQTTnet.Protocol.MqttQualityOfServiceLevel.AtLeastOnce)
            .Build();

        await _mqttClient.PublishAsync(msg);
        _logger.LogInformation($"Published {commandPayload} to {CommandTopic} for product {_lastReceivedQr}");
    }

    private static bool TryExtractQrValue(string topic, string payload, JsonElement? root, out string qrValue)
    {
        qrValue = string.Empty;

        if (root.HasValue)
        {
            if (root.Value.ValueKind == JsonValueKind.String && IsTopic(topic, "qr", "product", "barcode"))
            {
                qrValue = root.Value.GetString()?.Trim() ?? string.Empty;
            }
            else if (root.Value.ValueKind == JsonValueKind.Object)
            {
                foreach (var name in new[] { "qr", "productNumber", "product_number", "product", "code", "barcode" })
                {
                    if (root.Value.TryGetProperty(name, out var property))
                    {
                        qrValue = property.ValueKind == JsonValueKind.String
                            ? property.GetString()?.Trim() ?? string.Empty
                            : property.ToString().Trim();
                        break;
                    }
                }

                if (string.IsNullOrWhiteSpace(qrValue) &&
                    IsTopic(topic, "qr", "product", "barcode") &&
                    root.Value.TryGetProperty("value", out var valueProperty))
                {
                    qrValue = valueProperty.ValueKind == JsonValueKind.String
                        ? valueProperty.GetString()?.Trim() ?? string.Empty
                        : valueProperty.ToString().Trim();
                }
            }
        }

        if (string.IsNullOrWhiteSpace(qrValue) && IsTopic(topic, "qr", "product", "barcode"))
        {
            qrValue = payload.Trim().Trim('"');
        }

        return !string.IsNullOrWhiteSpace(qrValue);
    }

    private static bool TryExtractDouble(string fieldName, string topic, string payload, JsonElement? root, out double value)
    {
        value = 0;

        if (root.HasValue &&
            root.Value.ValueKind == JsonValueKind.Object &&
            root.Value.TryGetProperty(fieldName, out var property))
        {
            if (property.ValueKind == JsonValueKind.Number && property.TryGetDouble(out value))
            {
                return true;
            }

            if (property.ValueKind == JsonValueKind.String && TryParseDoubleLike(property.GetString(), out value))
            {
                return true;
            }
        }

        if (root.HasValue &&
            root.Value.ValueKind == JsonValueKind.Object &&
            IsTopic(topic, fieldName) &&
            root.Value.TryGetProperty("value", out var valueProperty))
        {
            if (valueProperty.ValueKind == JsonValueKind.Number && valueProperty.TryGetDouble(out value))
            {
                return true;
            }

            if (valueProperty.ValueKind == JsonValueKind.String && TryParseDoubleLike(valueProperty.GetString(), out value))
            {
                return true;
            }
        }

        return IsTopic(topic, fieldName) && TryParseDoubleLike(payload.Trim().Trim('"'), out value);
    }

    private static bool TryExtractBool(string fieldName, string topic, string payload, JsonElement? root, out bool value)
    {
        value = false;

        if (root.HasValue &&
            root.Value.ValueKind == JsonValueKind.Object &&
            root.Value.TryGetProperty(fieldName, out var property))
        {
            if (property.ValueKind == JsonValueKind.True || property.ValueKind == JsonValueKind.False)
            {
                value = property.GetBoolean();
                return true;
            }

            if (property.ValueKind == JsonValueKind.Number && property.TryGetInt32(out var numberValue))
            {
                value = numberValue != 0;
                return true;
            }

            if (property.ValueKind == JsonValueKind.String && TryParseBoolLike(property.GetString(), out value))
            {
                return true;
            }
        }

        if (root.HasValue &&
            root.Value.ValueKind == JsonValueKind.Object &&
            IsTopic(topic, fieldName, "smoke") &&
            root.Value.TryGetProperty("value", out var valueProperty))
        {
            if (valueProperty.ValueKind == JsonValueKind.True || valueProperty.ValueKind == JsonValueKind.False)
            {
                value = valueProperty.GetBoolean();
                return true;
            }

            if (valueProperty.ValueKind == JsonValueKind.Number && valueProperty.TryGetInt32(out var topicNumberValue))
            {
                value = topicNumberValue != 0;
                return true;
            }

            if (valueProperty.ValueKind == JsonValueKind.String && TryParseBoolLike(valueProperty.GetString(), out value))
            {
                return true;
            }
        }

        return IsTopic(topic, fieldName, "smoke") && TryParseBoolLike(payload.Trim().Trim('"'), out value);
    }

    private static bool IsTopic(string topic, params string[] names)
    {
        return names.Any(name => topic.Contains(name, StringComparison.OrdinalIgnoreCase));
    }

    private static bool TryParseBoolLike(string? rawValue, out bool value)
    {
        value = false;
        if (string.IsNullOrWhiteSpace(rawValue))
        {
            return false;
        }

        var normalized = rawValue.Trim();
        if (bool.TryParse(normalized, out value))
        {
            return true;
        }

        if (normalized == "1")
        {
            value = true;
            return true;
        }

        if (normalized == "0")
        {
            value = false;
            return true;
        }

        return false;
    }

    private static bool TryParseDoubleLike(string? rawValue, out double value)
    {
        value = 0;
        if (string.IsNullOrWhiteSpace(rawValue))
        {
            return false;
        }

        var normalized = rawValue.Trim();
        return double.TryParse(normalized, NumberStyles.Float, CultureInfo.InvariantCulture, out value)
            || double.TryParse(normalized, NumberStyles.Float, CultureInfo.CurrentCulture, out value);
    }
}
