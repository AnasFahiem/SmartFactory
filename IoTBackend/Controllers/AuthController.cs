using IoTBackend.Data;
using IoTBackend.Models;
using IoTBackend.Services;
using IoTBackend.Attributes;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;

namespace IoTBackend.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class AuthController : ControllerBase
    {
        private readonly AppDbContext _context;
        private readonly IConfiguration _configuration;

        public AuthController(AppDbContext context, IConfiguration configuration)
        {
            _context = context;
            _configuration = configuration;
        }

        [HttpPost("login")]
        public async Task<IActionResult> Login([FromBody] LoginDto loginDto)
        {
            if (loginDto == null || string.IsNullOrWhiteSpace(loginDto.Username) || string.IsNullOrWhiteSpace(loginDto.Password))
            {
                return BadRequest(new { message = "Username and password are required." });
            }

            try
            {
                var user = await _context.Users.FirstOrDefaultAsync(u => u.Username == loginDto.Username);
                if (user == null || !PasswordHasher.VerifyPassword(loginDto.Password, user.PasswordHash))
                {
                    return Unauthorized(new { message = "Invalid username or password." });
                }

                var sessionMinutes = _configuration.GetValue<int?>("Auth:SessionMinutes") ?? 480;
                var token = SessionManager.CreateSession(
                    user.Username,
                    user.Role,
                    TimeSpan.FromMinutes(sessionMinutes),
                    out var expiresAtUtc);

                return Ok(new
                {
                    token = token,
                    username = user.Username,
                    role = user.Role,
                    expiresAtUtc = expiresAtUtc
                });
            }
            catch (Exception ex)
            {
                Console.WriteLine($"❌ Login Database Exception: {ex.Message}");
                return StatusCode(500, new 
                { 
                    message = "Database connection error.",
                    details = ex.Message,
                    innerDetails = ex.InnerException?.Message 
                });
            }
        }

        [HttpPost("register")]
        [CustomAuthorize(Roles = "Admin")]
        public async Task<IActionResult> Register([FromBody] RegisterDto registerDto)
        {
            if (registerDto == null || string.IsNullOrWhiteSpace(registerDto.Username) || string.IsNullOrWhiteSpace(registerDto.Password))
            {
                return BadRequest(new { message = "Username and password are required." });
            }

            try
            {
                var existingUser = await _context.Users.FirstOrDefaultAsync(u => u.Username == registerDto.Username);
                if (existingUser != null)
                {
                    return BadRequest(new { message = "Username already exists." });
                }

                var requestedRole = string.IsNullOrWhiteSpace(registerDto.Role) ? "User" : registerDto.Role;
                if (!RolePolicy.TryNormalize(requestedRole, out var normalizedRole))
                {
                    return BadRequest(new { message = "Invalid role. Allowed roles are User, Manager, and Admin." });
                }

                var newUser = new User
                {
                    Username = registerDto.Username,
                    PasswordHash = PasswordHasher.HashPassword(registerDto.Password),
                    Role = normalizedRole,
                    Email = registerDto.Email
                };

                _context.Users.Add(newUser);
                await _context.SaveChangesAsync();

                return Ok(new
                {
                    message = "User registered successfully.",
                    username = newUser.Username,
                    role = newUser.Role
                });
            }
            catch (Exception ex)
            {
                Console.WriteLine($"❌ Register Database Exception: {ex.Message}");
                return StatusCode(500, new 
                { 
                    message = "Database connection error.",
                    details = ex.Message,
                    innerDetails = ex.InnerException?.Message 
                });
            }
        }

        [HttpGet("me")]
        [CustomAuthorize]
        public IActionResult GetMyProfile()
        {
            if (!TryGetCurrentSession(out _, out var session))
            {
                return Unauthorized(new { message = "Invalid session." });
            }

            return Ok(new
            {
                username = session.Username,
                role = session.Role,
                expiresAtUtc = session.ExpiresAtUtc
            });
        }

        [HttpPost("logout")]
        [CustomAuthorize]
        public IActionResult Logout()
        {
            if (!TryGetCurrentSession(out var token, out _))
            {
                return Unauthorized(new { message = "Invalid session." });
            }

            SessionManager.RemoveSession(token);
            return Ok(new { message = "Logged out successfully." });
        }

        [HttpPut("me")]
        [CustomAuthorize]
        public async Task<IActionResult> UpdateMyProfile([FromBody] UpdateProfileDto dto)
        {
            if (!TryGetCurrentSession(out var token, out var session))
            {
                return Unauthorized(new { message = "Invalid session." });
            }

            var currentUsername = session.Username;

            var user = await _context.Users.FirstOrDefaultAsync(u => u.Username == currentUsername);
            if (user == null)
                return NotFound(new { message = "User not found." });

            if (!string.IsNullOrWhiteSpace(dto.Username) && dto.Username != currentUsername)
            {
                var existing = await _context.Users.FirstOrDefaultAsync(u => u.Username == dto.Username);
                if (existing != null)
                {
                    return BadRequest(new { message = "Username already exists." });
                }
                user.Username = dto.Username;
            }

            if (!string.IsNullOrWhiteSpace(dto.Password))
            {
                user.PasswordHash = PasswordHasher.HashPassword(dto.Password);
            }

            if (dto.Email != null)
            {
                user.Email = dto.Email;
            }

            await _context.SaveChangesAsync();

            if (!string.IsNullOrWhiteSpace(dto.Username) && dto.Username != currentUsername)
            {
                SessionManager.RemoveSession(token);
                return Ok(new { message = "Profile updated. Please log in again.", requireRelogin = true });
            }

            return Ok(new { message = "Profile updated successfully.", requireRelogin = false });
        }

        private bool TryGetCurrentSession(out string token, out SessionManager.UserSession session)
        {
            token = string.Empty;
            session = new SessionManager.UserSession();
            var authHeader = HttpContext.Request.Headers["Authorization"].ToString();
            return SessionManager.TryGetBearerToken(authHeader, out token)
                && SessionManager.TryGetSession(token, out session);
        }
    }

    public class LoginDto
    {
        public string Username { get; set; } = string.Empty;
        public string Password { get; set; } = string.Empty;
    }

    public class RegisterDto
    {
        public string Username { get; set; } = string.Empty;
        public string Password { get; set; } = string.Empty;
        public string Role { get; set; } = "User";
        public string? Email { get; set; }
    }

    public class UpdateProfileDto
    {
        public string? Username { get; set; }
        public string? Password { get; set; }
        public string? Email { get; set; }
    }
}
