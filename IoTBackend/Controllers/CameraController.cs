using IoTBackend.Hubs;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.SignalR;
using Microsoft.Extensions.Configuration;

namespace IoTBackend.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class CameraController : ControllerBase
    {
        private readonly IHubContext<FactoryHub> _hubContext;
        private readonly string _cameraSecret;

        // In a real app, you might store these in a database or a service
        private static bool _isCameraRunning = true;
        private static string _currentSource = "0";

        public CameraController(
            IHubContext<FactoryHub> hubContext,
            IConfiguration configuration,
            IWebHostEnvironment environment)
        {
            _hubContext = hubContext;
            var configuredSecret = configuration["Camera:SecretKey"];
            if (string.IsNullOrWhiteSpace(configuredSecret))
            {
                configuredSecret = Environment.GetEnvironmentVariable("CAMERA_SECRET");
            }

            if (string.IsNullOrWhiteSpace(configuredSecret))
            {
                if (!environment.IsDevelopment())
                {
                    throw new InvalidOperationException("Camera:SecretKey or CAMERA_SECRET must be configured.");
                }

                configuredSecret = "dev-camera-secret";
            }

            _cameraSecret = configuredSecret;
        }

        // 1. Existing Upload Endpoint (Used by Python/Phone Bridge)
        [HttpPost("upload")]
        public async Task<IActionResult> UploadFrame([FromBody] CameraFrameRequest request)
        {
            if (!string.Equals(request.SecretKey, _cameraSecret, StringComparison.Ordinal))
                return Unauthorized();

            await _hubContext.Clients.All.SendAsync("ReceiveCameraFrame", request.Image);

            // Broadcast the AI stats to the Angular frontend
            await _hubContext.Clients.All.SendAsync("ReceiveStatsUpdate", new
            {
                total_people = request.TotalPeople,
                violations = request.Violations
            });

            return Ok();
        }

        // 2. NEW: Toggle Endpoint (Fixes your 404)
        [HttpPost("toggle")]
        public IActionResult ToggleCamera([FromBody] CameraActionRequest request)
        {
            _isCameraRunning = request.Action == "start";

            return Ok(new
            {
                is_running = _isCameraRunning,
                message = $"Camera {request.Action}ed successfully"
            });
        }

        // 3. NEW: Config Endpoint (Fixes your other potential 404)
        [HttpPost("config")]
        public IActionResult SetSource([FromBody] CameraConfigSource request)
        {
            _currentSource = request.Source;
            return Ok(new
            {
                message = $"Source updated to {request.Source}"
            });
        }
    }

    // Helper Classes for Data Mapping
    public class CameraFrameRequest
    {
        public string Image { get; set; } = string.Empty;
        public string SecretKey { get; set; } = string.Empty;
        public int TotalPeople { get; set; }
        public int Violations { get; set; }
    }

    public class CameraActionRequest
    {
        public string Action { get; set; } = string.Empty;
    }

    public class CameraConfigSource
    {
        public string Source { get; set; } = string.Empty;
    }
}
