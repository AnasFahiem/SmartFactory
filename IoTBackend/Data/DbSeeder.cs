using IoTBackend.Models;
using IoTBackend.Services;
using Microsoft.EntityFrameworkCore;

namespace IoTBackend.Data
{
    public static class DbSeeder
    {
        public static async Task SeedUsersAsync(AppDbContext context)
        {
            var adminUser = await context.Users.FirstOrDefaultAsync(u => u.Username == "admin");
            if (adminUser == null)
            {
                var newAdmin = new User
                {
                    Username = "admin",
                    PasswordHash = PasswordHasher.HashPassword("admin123"),
                    Role = "Admin"
                };
                context.Users.Add(newAdmin);
                await context.SaveChangesAsync();
                Console.WriteLine("✅ Default admin user created successfully (Username: admin, Password: admin123).");
            }
        }
    }
}
