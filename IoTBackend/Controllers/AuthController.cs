using IoTBackend.Data;
using IoTBackend.Models;
using IoTBackend.Services;
using IoTBackend.Attributes;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace IoTBackend.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class AuthController : ControllerBase
    {
        private readonly AppDbContext _context;

        public AuthController(AppDbContext context)
        {
            _context = context;
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

                var token = SessionManager.CreateSession(user.Username, user.Role);

                return Ok(new
                {
                    token = token,
                    username = user.Username,
                    role = user.Role
                });
            }
            catch (Exception ex)
            {
                Console.WriteLine($"❌ Login Database Exception: {ex.Message}");
                return StatusCode(500, new 
                { 
                    message = "Database connection error on Azure.", 
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

                var newUser = new User
                {
                    Username = registerDto.Username,
                    PasswordHash = PasswordHasher.HashPassword(registerDto.Password),
                    Role = string.IsNullOrWhiteSpace(registerDto.Role) ? "User" : registerDto.Role
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
                    message = "Database connection error on Azure.", 
                    details = ex.Message,
                    innerDetails = ex.InnerException?.Message 
                });
            }
        }

        [HttpPut("me")]
        [CustomAuthorize]
        public async Task<IActionResult> UpdateMyProfile([FromBody] UpdateProfileDto dto)
        {
            var authHeader = HttpContext.Request.Headers["Authorization"].ToString();
            var token = authHeader.Substring("Bearer ".Length).Trim();
            var currentUsername = SessionManager.GetUsername(token);

            if (string.IsNullOrEmpty(currentUsername))
                return Unauthorized(new { message = "Invalid session." });

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

            await _context.SaveChangesAsync();

            if (!string.IsNullOrWhiteSpace(dto.Username) && dto.Username != currentUsername)
            {
                SessionManager.RemoveSession(token);
                return Ok(new { message = "Profile updated. Please log in again.", requireRelogin = true });
            }

            return Ok(new { message = "Profile updated successfully.", requireRelogin = false });
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
    }
}
