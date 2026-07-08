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
var port = Environment.GetEnvironmentVariable("PORT") ?? "5005";
builder.WebHost.UseUrls($"http://*:{port}");

// 2. DATABASE CONFIGURATION
var connectionString = builder.Configuration.GetConnectionString("DefaultConnection")
    ?? throw new InvalidOperationException("ConnectionStrings:DefaultConnection is not configured.");

var serverVersion = new MySqlServerVersion(new Version(8, 0, 30));

builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseMySql(
        connectionString,
        serverVersion,
        mySqlOptions =>
        {
            mySqlOptions.EnableRetryOnFailure(
                maxRetryCount: 3,
                maxRetryDelay: TimeSpan.FromSeconds(10),
                errorNumbersToAdd: null
            );
        }
    ));

// 3. MQTT & BACKGROUND SERVICES
builder.Services.AddSingleton<IMqttClient>(_ => new MqttFactory().CreateMqttClient());
builder.Services.AddHostedService<MqttService>();

// 4. SIGNALR & LARGE PAYLOAD CONFIGURATION
builder.Services.AddSignalR(options =>
{
    options.MaximumReceiveMessageSize = 1024 * 1024; // 1MB
});

builder.Services.Configure<FormOptions>(options =>
{
    options.ValueLengthLimit = int.MaxValue;
    options.MultipartBodyLengthLimit = int.MaxValue;
    options.MemoryBufferThreshold = int.MaxValue;
});

builder.Services.AddControllers();

// 5. CORS CONFIGURATION
var configuredOrigins = builder.Configuration.GetSection("Cors:AllowedOrigins")
    .GetChildren()
    .Select(origin => origin.Value)
    .Where(origin => !string.IsNullOrWhiteSpace(origin))
    .Cast<string>()
    .ToArray();
var allowedOrigins = configuredOrigins.Length > 0
    ? configuredOrigins
    : new[]
    {
        "https://smart-factory-client.azurewebsites.net",
        "http://localhost:4200",
        "https://localhost:4200"
    };

builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowFrontend", policy =>
    {
        policy.WithOrigins(allowedOrigins)
              .AllowAnyMethod()
              .AllowAnyHeader()
              .AllowCredentials();
    });
});

var app = builder.Build();

// 6. HEALTH CHECK (Azure Warmup Fix)
app.MapGet("/", () => "IoT Backend is Online");

app.MapGet("/health", () => Results.Ok(new { status = "Alive" })).AllowAnonymous();
app.MapGet("/health/live", () => Results.Ok(new { status = "Alive" })).AllowAnonymous();

app.MapGet("/health/ready", async (AppDbContext dbContext) =>
{
    try
    {
        var count = await dbContext.Products.CountAsync();
        return Results.Ok(new { status = "Ready", database = "Connected", productCount = count });
    }
    catch (Exception ex)
    {
        var realError = ex.InnerException != null ? ex.InnerException.Message : ex.Message;
        return Results.Problem(detail: realError, title: "Database Connection Failed");
    }
}).AllowAnonymous();

// 7. ASYNC DATABASE MIGRATIONS
_ = Task.Run(async () =>
{
    try
    {
        using var scope = app.Services.CreateScope();
        var dbContext = scope.ServiceProvider.GetRequiredService<AppDbContext>();
        await dbContext.Database.MigrateAsync();
        Console.WriteLine("✅ Database Migration Finished.");
        // Make sure DbSeeder exists in your project, otherwise comment this out:
        await DbSeeder.SeedUsersAsync(dbContext, app.Configuration);
    }
    catch (Exception ex)
    {
        Console.WriteLine($"❌ Migration Background Error: {ex.Message}");
    }
});

// 8. MIDDLEWARE PIPELINE
app.UseRouting();
app.UseCors("AllowFrontend");

app.MapControllers();
app.MapHub<FactoryHub>("/hubs/factory");

app.Run();
