using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using IoTBackend.Data;
using IoTBackend.Attributes;
using System.Linq;
using System.Threading.Tasks;

namespace IoTBackend.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    [CustomAuthorize(Roles = "Admin")]
    public class UsersController : ControllerBase
    {
        private readonly AppDbContext _context;

        public UsersController(AppDbContext context)
        {
            _context = context;
        }

        // GET: api/users
        [HttpGet]
        public async Task<IActionResult> GetUsers()
        {
            // Do not return the password hashes to the frontend
            var users = await _context.Users
                .Select(u => new
                {
                    u.Id,
                    u.Username,
                    u.Role
                })
                .ToListAsync();

            return Ok(users);
        }

        // DELETE: api/users/{id}
        [HttpDelete("{id}")]
        public async Task<IActionResult> DeleteUser(int id)
        {
            var user = await _context.Users.FindAsync(id);
            if (user == null)
            {
                return NotFound(new { message = "User not found." });
            }

            // Prevent deleting the default admin account to avoid lockouts
            if (user.Username.ToLower() == "admin")
            {
                return BadRequest(new { message = "Cannot delete the default admin user." });
            }

            _context.Users.Remove(user);
            await _context.SaveChangesAsync();

            return Ok(new { message = "User deleted successfully." });
        }

        // PUT: api/users/{id}/role
        [HttpPut("{id}/role")]
        public async Task<IActionResult> UpdateUserRole(int id, [FromBody] UpdateRoleDto updateRoleDto)
        {
            var user = await _context.Users.FindAsync(id);
            if (user == null)
            {
                return NotFound(new { message = "User not found." });
            }

            // Prevent changing the default admin role
            if (user.Username.ToLower() == "admin")
            {
                return BadRequest(new { message = "Cannot change role of the default admin user." });
            }

            if (string.IsNullOrWhiteSpace(updateRoleDto.Role))
            {
                return BadRequest(new { message = "Role is required." });
            }

            user.Role = updateRoleDto.Role;
            await _context.SaveChangesAsync();

            return Ok(new { message = "User role updated successfully.", role = user.Role });
        }
    }

    public class UpdateRoleDto
    {
        public string Role { get; set; } = string.Empty;
    }
}
