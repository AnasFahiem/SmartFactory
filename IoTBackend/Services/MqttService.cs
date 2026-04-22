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

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        var options = new MqttClientOptionsBuilder()
    .WithTcpServer("158d9042fc2542248a400b91e6b8c138.s1.eu.hivemq.cloud", 8883)
    .WithCredentials("iotuser", "12345678Me")
    .WithTlsOptions(o =>
    {
        o.UseTls();
        // HiveMQ Cloud uses public CA certificates, so this is required:
        o.WithSslProtocols(System.Security.Authentication.SslProtocols.Tls12);
    })
    .WithCleanSession()
    .Build();

        _mqttClient.ApplicationMessageReceivedAsync += HandleMessageAsync;

        // Run connection logic in a separate task so it doesn't block Web App startup
        _ = Task.Run(async () =>
        {
            while (!stoppingToken.IsCancellationRequested)
            {
                try
                {
                    if (!_mqttClient.IsConnected)
                    {
                        await _mqttClient.ConnectAsync(options, stoppingToken);
                        await _mqttClient.SubscribeAsync("factory/#"); // Subscribe to all factory topics
                        _logger.LogInformation("MQTT Connected and Subscribed.");
                    }
                }
                catch (Exception ex)
                {
                    _logger.LogError($"MQTT Connection failed: {ex.Message}");
                }
                await Task.Delay(5000, stoppingToken); // Check connection every 5s
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
            // 1. Parse the JSON from the ESP32
            // We use JsonDocument to handle the dynamic nature of the payload
            using var doc = JsonDocument.Parse(payload);
            var root = doc.RootElement;

            // 2. Broadcast specific values to the SignalR listeners in Angular
            if (root.TryGetProperty("temperature", out var temp))
                await _hubContext.Clients.All.SendAsync("ReceiveTemperatureUpdate", temp.GetDouble());

            if (root.TryGetProperty("humidity", out var hum))
                await _hubContext.Clients.All.SendAsync("ReceiveHumidityUpdate", hum.GetDouble());

            if (root.TryGetProperty("weight", out var weight))
                await _hubContext.Clients.All.SendAsync("ReceiveWeightUpdate", weight.GetDouble());

            if (root.TryGetProperty("qr", out var qr))
                await _hubContext.Clients.All.SendAsync("ReceiveProductNumberUpdate", qr.GetString());

            if (root.TryGetProperty("gas_alarm", out var gas))
                await _hubContext.Clients.All.SendAsync("ReceiveSmokeUpdate", gas.GetBoolean());

            // 3. Update the Stats (Total People / Violations)
            // Since the ESP32 doesn't know about people, we usually get this from the Python Bridge,
            // but we can send a "Status Update" here to keep the dashboard alive.
            await _hubContext.Clients.All.SendAsync("ReceiveStatsUpdate", new
            {
                total_people = 0, // This will be updated by your CameraController
                violations = 0
            });

            // 4. Handle AI Alert from Python Monitor
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

        // 4. SAVE to MySQL (Optional - keep your existing scope logic)
        using (var scope = _scopeFactory.CreateScope())
        {
            var dbContext = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            // Add DB logic here if needed
        }
    }
}
