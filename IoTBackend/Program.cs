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
var port = Environment.GetEnvironmentVariable("PORT") ?? "8080";
builder.WebHost.UseUrls($"http://*:{port}");

// 2. DATABASE CONFIGURATION
// Note: I changed "smartfacory" to "smartfactory" here just in case it was a typo!
var connectionString = builder.Configuration.GetConnectionString("DefaultConnection")
    ?? "Server=smartfacory.mysql.database.azure.com;Database=iotdb;Uid=mikha;Pwd=12345678Me@;SslMode=Required";

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
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowFrontend", policy =>
    {
        policy.WithOrigins("https://smart-factory-client.azurewebsites.net")
              .AllowAnyMethod()
              .AllowAnyHeader()
              .AllowCredentials();
    });
});

var app = builder.Build();

// 6. HEALTH CHECK (Azure Warmup Fix)
app.MapGet("/", () => "IoT Backend is Online");

app.MapGet("/health", async (AppDbContext dbContext) =>
{
    try
    {
        var count = await dbContext.Products.CountAsync();
        return Results.Ok(new { status = "Healthy", database = "Connected", productCount = count });
    }
    catch (Exception ex)
    {
        // THIS IS THE CRUCIAL CHANGE: We are now grabbing the InnerException
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
        await DbSeeder.SeedUsersAsync(dbContext);
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