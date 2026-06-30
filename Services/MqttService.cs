using MQTTnet;
using MQTTnet.Client;
using Microsoft.AspNetCore.SignalR;
using IoTBackend.Hubs;
using IoTBackend.Data;
using IoTBackend.Models;
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

    // ==========================================
    // NEW: Token to control the 1-second retry loop
    // ==========================================
    private CancellationTokenSource? _weightRequestCts;

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
                .WithTopic("factory/commands")
                .WithPayload("GET_WEIGHT") 
                .WithQualityOfServiceLevel(MQTTnet.Protocol.MqttQualityOfServiceLevel.AtLeastOnce)
                .Build();

            await _mqttClient.PublishAsync(message);
            _logger.LogInformation("Sent GET_WEIGHT command to ESP32.");
        }
        else
        {
            _logger.LogWarning("Cannot request weight: MQTT Client is not connected.");
        }
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        var options = new MqttClientOptionsBuilder()
            .WithTcpServer("158d9042fc2542248a400b91e6b8c138.s1.eu.hivemq.cloud", 8883)
            .WithCredentials("iotuser", "12345678Me")
            .WithTlsOptions(o =>
            {
                o.UseTls();
                o.WithSslProtocols(System.Security.Authentication.SslProtocols.Tls12);
            })
            .WithCleanSession()
            .Build();

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
                        await _mqttClient.SubscribeAsync("factory/#"); 
                        _logger.LogInformation("MQTT Connected and Subscribed.");
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

        try
        {
            using var doc = JsonDocument.Parse(payload);
            var root = doc.RootElement;

            if (root.TryGetProperty("temperature", out var temp))
                await _hubContext.Clients.All.SendAsync("ReceiveTemperatureUpdate", temp.GetDouble());

            if (root.TryGetProperty("humidity", out var hum))
                await _hubContext.Clients.All.SendAsync("ReceiveHumidityUpdate", hum.GetDouble());

            // ==========================================
            // UPDATED: Stop the loop when weight arrives
            // ==========================================
            if (root.TryGetProperty("weight", out var weight))
            {
                // Stop the 1-second retry loop
                _weightRequestCts?.Cancel(); 
                _logger.LogInformation("Weight received! Stopped sending requests.");

                await _hubContext.Clients.All.SendAsync("ReceiveWeightUpdate", weight.GetDouble());
            }

            // ==========================================
            // UPDATED: Start the loop when QR arrives
            // ==========================================
            if (root.TryGetProperty("qr", out var qr))
            {
                string qrValue = qr.GetString();
                
                await _hubContext.Clients.All.SendAsync("ReceiveProductNumberUpdate", qrValue);
                
                _logger.LogInformation($"QR Code received: {qrValue}. Starting 1-second weight request loop...");

                // Cancel any old loop just in case one is still running
                _weightRequestCts?.Cancel();
                _weightRequestCts = new CancellationTokenSource();
                
                var token = _weightRequestCts.Token;

                // Start a background loop that fires every 1 second
                _ = Task.Run(async () =>
                {
                    try
                    {
                        while (!token.IsCancellationRequested)
                        {
                            await RequestWeightAsync();
                            await Task.Delay(1000, token); // Wait exactly 1 second before looping
                        }
                    }
                    catch (TaskCanceledException)
                    {
                        // Safely catches the cancellation when the loop stops
                    }
                }, token);
            }

            if (root.TryGetProperty("gas_alarm", out var gas))
                await _hubContext.Clients.All.SendAsync("ReceiveSmokeUpdate", gas.GetBoolean());

            await _hubContext.Clients.All.SendAsync("ReceiveStatsUpdate", new
            {
                total_people = 0, 
                violations = 0
            });

            if (root.TryGetProperty("ai_alert", out var aiAlert) && aiAlert.GetBoolean())
            {
                string msgText = root.TryGetProperty("message", out var msgNode) ? msgNode.GetString() : "AI Anomaly Detected!";
                await _hubContext.Clients.All.SendAsync("ReceiveAiAlert", msgText);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error parsing MQTT JSON: {ex.Message}");
        }

        using (var scope = _scopeFactory.CreateScope())
        {
            var dbContext = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            // Add DB logic here if needed
        }
    }
}