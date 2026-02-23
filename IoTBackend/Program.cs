using IoTBackend.Data;
using IoTBackend.Hubs;
using IoTBackend.Services;
using MQTTnet;
using MQTTnet.Client;
using Microsoft.EntityFrameworkCore;
using Microsoft.AspNetCore.Http.Features;
using Microsoft.AspNetCore.SignalR;

var builder = WebApplication.CreateBuilder(args);

// 1. DYNAMIC PORT FOR AZURE
// Azure App Service specifies the port your app must listen on via the PORT environment variable.
var port = Environment.GetEnvironmentVariable("PORT") ?? "8080";
builder.WebHost.UseUrls($"http://*:{port}");

// 2. DATABASE CONFIGURATION
var connectionString = builder.Configuration.GetConnectionString("DefaultConnection")
    ?? "Server=smartest-factory-server.mysql.database.azure.com;Database=iotdb;Uid=mikha;Pwd=your_password;SslMode=Required";

var serverVersion = new MySqlServerVersion(new Version(8, 0, 30));

builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseMySql(connectionString, serverVersion));

// 3. MQTT & BACKGROUND SERVICES
builder.Services.AddSingleton<IMqttClient>(_ => new MqttFactory().CreateMqttClient());
builder.Services.AddHostedService<MqttService>();

// 4. SIGNALR & LARGE PAYLOAD CONFIGURATION
// We increase the limits to allow base64 camera frames (approx 1MB per frame).
builder.Services.AddSignalR(options =>
{
    options.MaximumReceiveMessageSize = 1024 * 1024; // 1MB
});

// Configure Kestrel and Form limits for the Camera Upload POST request
builder.Services.Configure<FormOptions>(options =>
{
    options.ValueLengthLimit = int.MaxValue;
    options.MultipartBodyLengthLimit = int.MaxValue;
    options.MemoryBufferThreshold = int.MaxValue;
});

builder.Services.AddControllers();

// 5. CORS CONFIGURATION
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowFrontend", policy =>
    {
        policy.WithOrigins("https://smart-factory-client.azurewebsites.net")
              .AllowAnyMethod()
              .AllowAnyHeader()
              .AllowCredentials(); // Essential for SignalR
    });
});

var app = builder.Build();

// 6. HEALTH CHECK (Azure Warmup Fix)
// Responds 200 OK immediately so Azure knows the container is ready.
app.MapGet("/", () => "IoT Backend is Online");
app.MapGet("/health", () => Results.Ok("Healthy")).AllowAnonymous();

// 7. ASYNC DATABASE MIGRATIONS
// Running migrations in the background prevents "RequestTimeout" during Azure startup.
_ = Task.Run(async () =>
{
    try
    {
        using var scope = app.Services.CreateScope();
        var dbContext = scope.ServiceProvider.GetRequiredService<AppDbContext>();
        await dbContext.Database.MigrateAsync();
        Console.WriteLine("✅ Database Migration Finished.");
    }
    catch (Exception ex)
    {
        Console.WriteLine($"❌ Migration Background Error: {ex.Message}");
    }
});

// 8. MIDDLEWARE PIPELINE
// Important: UseCors must be placed between UseRouting and Map endpoints.
app.UseRouting();
app.UseCors("AllowFrontend");

app.MapControllers();
app.MapHub<FactoryHub>("/hubs/factory");

app.Run();