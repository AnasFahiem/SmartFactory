using MQTTnet;
using MQTTnet.Client;
using System.Text.Json;
using System.Text;
using IoTBackend.Models;
using IoTBackend.Data;
using IoTBackend.Hubs;
using Microsoft.AspNetCore.SignalR;

namespace IoTBackend.Services
{
    public class MqttService
    {
        private readonly IMqttClient _mqttClient;
        private readonly IHubContext<FactoryHub> _hubContext;
        private readonly IServiceScopeFactory _scopeFactory;
        private readonly ILogger<MqttService> _logger;
        private readonly IConfiguration _configuration;

        public MqttService(IMqttClient mqttClient, IHubContext<FactoryHub> hubContext, IServiceScopeFactory scopeFactory, ILogger<MqttService> logger, IConfiguration configuration)
        {
            _mqttClient = mqttClient;
            _hubContext = hubContext;
            _scopeFactory = scopeFactory;
            _logger = logger;
            _configuration = configuration;
        }

        public async Task StartAsync()
        {
            var mqttSection = _configuration.GetSection("Mqtt");
            var host = mqttSection.GetValue<string>("Host") ?? "localhost";
            var port = mqttSection.GetValue<int>("Port");
            var useTls = mqttSection.GetValue<bool>("UseTls", false);
            var clientId = mqttSection.GetValue<string>("ClientId") ?? Guid.NewGuid().ToString();
            var username = mqttSection.GetValue<string>("Username");
            var password = mqttSection.GetValue<string>("Password");

            var builder = new MqttClientOptionsBuilder()
                .WithClientId(clientId)
                .WithTcpServer(host, port);

            if (!string.IsNullOrEmpty(username))
            {
                builder = builder.WithCredentials(username, password);
            }

            if (useTls)
            {
                builder = builder.WithTlsOptions(o => { o.UseTls(); });
            }

            var options = builder.Build();

            _mqttClient.DisconnectedAsync += async e =>
            {
                _logger.LogWarning("MQTT disconnected");
                await Task.Delay(5000);
                await _mqttClient.ConnectAsync(options);
            };

            _mqttClient.ApplicationMessageReceivedAsync += HandleMessageAsync;

            await _mqttClient.ConnectAsync(options);

            var topics = mqttSection.GetSection("Topics").Get<string[]>() ?? new[] { "factory/measurement", "factory/temperature", "factory/smoke", "factory/weight", "factory/product" };
            var subscribeBuilder = new MqttClientSubscribeOptionsBuilder();
            foreach (var t in topics)
            {
                subscribeBuilder = subscribeBuilder.WithTopicFilter(t);
            }
            var subscribeOptions = subscribeBuilder.Build();

            await _mqttClient.SubscribeAsync(subscribeOptions);
            _logger.LogInformation("MQTT subscribed to factory topics");
        }

        private async Task HandleMessageAsync(MqttApplicationMessageReceivedEventArgs e)
        {
            try
            {
                var segment = e.ApplicationMessage.PayloadSegment;
                string payload = Encoding.UTF8.GetString(segment.Array!, segment.Offset, segment.Count);
                string topic = e.ApplicationMessage.Topic;

                _logger.LogInformation($"MQTT message received - Topic: {topic}, Payload: {payload}");

                // Parse JSON payload
                var json = JsonDocument.Parse(payload);

                // Handle batch measurement topic (all sensors in one message)
                if (topic == "factory/measurement")
                {
                    var root = json.RootElement;

                    // Extract and broadcast temperature
                    if (root.TryGetProperty("temperature", out var tempElement))
                    {
                        decimal temperature = tempElement.GetDecimal();
                        await _hubContext.Clients.All.SendAsync("ReceiveTemperatureUpdate", temperature);
                        _logger.LogInformation($"Temperature: {temperature}");
                    }

                    // Extract and broadcast smoke
                    if (root.TryGetProperty("smoke", out var smokeElement))
                    {
                        bool smoke = smokeElement.GetBoolean();
                        await _hubContext.Clients.All.SendAsync("ReceiveSmokeUpdate", smoke);
                        _logger.LogInformation($"Smoke: {smoke}");
                    }

                    // Extract and broadcast weight
                    decimal? weight = null;
                    if (root.TryGetProperty("weight", out var weightElement))
                    {
                        weight = weightElement.GetDecimal();
                        await _hubContext.Clients.All.SendAsync("ReceiveWeightUpdate", weight.Value);
                        _logger.LogInformation($"Weight: {weight}");
                    }

                    // Extract and broadcast product number
                    string? productNumber = null;
                    if (root.TryGetProperty("productNumber", out var productElement))
                    {
                        productNumber = productElement.GetString();
                        await _hubContext.Clients.All.SendAsync("ReceiveProductNumberUpdate", productNumber);
                        _logger.LogInformation($"Product: {productNumber}");
                    }

                    // Save to database if we have weight or productNumber
                    if (weight.HasValue || !string.IsNullOrEmpty(productNumber))
                    {
                        using (var scope = _scopeFactory.CreateScope())
                        {
                            var dbContext = scope.ServiceProvider.GetRequiredService<AppDbContext>();
                            var product = new Product
                            {
                                Weight = weight,
                                ProductNumber = productNumber
                            };
                            dbContext.Products.Add(product);
                            await dbContext.SaveChangesAsync();
                            _logger.LogInformation($"Saved to database - Product: {productNumber}, Weight: {weight}");
                        }
                    }
                }
                // Handle individual sensor topics
                else if (topic == "factory/temperature")
                {
                    decimal temperature = json.RootElement.GetProperty("value").GetDecimal();
                    await _hubContext.Clients.All.SendAsync("ReceiveTemperatureUpdate", temperature);
                }
                else if (topic == "factory/smoke")
                {
                    bool smoke = json.RootElement.GetProperty("value").GetBoolean();
                    await _hubContext.Clients.All.SendAsync("ReceiveSmokeUpdate", smoke);
                }
                else if (topic == "factory/weight")
                {
                    decimal weight = json.RootElement.GetProperty("value").GetDecimal();
                    await _hubContext.Clients.All.SendAsync("ReceiveWeightUpdate", weight);

                    using (var scope = _scopeFactory.CreateScope())
                    {
                        var dbContext = scope.ServiceProvider.GetRequiredService<AppDbContext>();
                        var product = new Product { Weight = weight };
                        dbContext.Products.Add(product);
                        await dbContext.SaveChangesAsync();
                        _logger.LogInformation($"Saved weight {weight} to database");
                    }
                }
                else if (topic == "factory/product")
                {
                    string? productNumber = json.RootElement.GetProperty("value").GetString();
                    await _hubContext.Clients.All.SendAsync("ReceiveProductNumberUpdate", productNumber);

                    using (var scope = _scopeFactory.CreateScope())
                    {
                        var dbContext = scope.ServiceProvider.GetRequiredService<AppDbContext>();
                        var product = new Product { ProductNumber = productNumber };
                        dbContext.Products.Add(product);
                        await dbContext.SaveChangesAsync();
                        _logger.LogInformation($"Saved product {productNumber} to database");
                    }
                }
                else
                {
                    // Handle any other topics dynamically
                    _logger.LogInformation($"Received message on unhandled topic: {topic}");
                    // Broadcast to SignalR with generic method
                    await _hubContext.Clients.All.SendAsync("ReceiveGenericUpdate", new { topic, payload });
                }
            }
            catch (Exception ex)
            {
                _logger.LogError($"Error processing MQTT message: {ex.Message}");
            }
        }
    }
}
