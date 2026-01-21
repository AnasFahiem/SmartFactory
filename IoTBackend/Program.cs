using IoTBackend.Data;
using IoTBackend.Hubs;
using IoTBackend.Services;
using MQTTnet;
using Microsoft.EntityFrameworkCore;
using Pomelo.EntityFrameworkCore.MySql;

var builder = WebApplication.CreateBuilder(args);

// Add DbContext
var connectionString = builder.Configuration.GetConnectionString("DefaultConnection") ?? "Server=localhost;Database=IotDb;User=springstudent;Password=springstudent;";
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseMySql(connectionString, ServerVersion.AutoDetect(connectionString)));

// Add MQTT and SignalR
builder.Services.AddSingleton<MQTTnet.Client.IMqttClient>(_ => new MqttFactory().CreateMqttClient());
builder.Services.AddSingleton<MqttService>();
builder.Services.AddSignalR();

// Add Controllers
builder.Services.AddControllers();

// Add CORS
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowFrontend", policy =>
    {
        policy.WithOrigins("http://localhost:4200")
              .AllowAnyMethod()
              .AllowAnyHeader()
              .AllowCredentials();
    });
});

var app = builder.Build();

// Apply migrations
using (var scope = app.Services.CreateScope())
{
    var dbContext = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    dbContext.Database.Migrate();
}

app.UseHttpsRedirection();
app.UseRouting();
app.UseCors("AllowFrontend");

app.MapControllers();
app.MapHub<FactoryHub>("/hubs/factory");

// Start MQTT service
var mqttService = app.Services.GetRequiredService<MqttService>();
_ = mqttService.StartAsync();

app.Run();
