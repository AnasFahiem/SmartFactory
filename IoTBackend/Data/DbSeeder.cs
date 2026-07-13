using IoTBackend.Models;
using IoTBackend.Services;
using Microsoft.EntityFrameworkCore;

namespace IoTBackend.Data
{
    public static class DbSeeder
    {
        public static async Task SeedUsersAsync(AppDbContext context, IConfiguration configuration)
        {
            var adminUsername = configuration["DefaultAdmin:Username"];
            var adminPassword = configuration["DefaultAdmin:Password"];

            if (string.IsNullOrWhiteSpace(adminUsername) || string.IsNullOrWhiteSpace(adminPassword))
            {
                Console.WriteLine("Default admin seed skipped. Configure DefaultAdmin:Username and DefaultAdmin:Password to seed one.");
                return;
            }

            var adminUser = await context.Users.FirstOrDefaultAsync(u => u.Username == adminUsername);
            if (adminUser != null)
            {
                return;
            }

            var newAdmin = new User
            {
                Username = adminUsername,
                PasswordHash = PasswordHasher.HashPassword(adminPassword),
                Role = "Admin"
            };

            context.Users.Add(newAdmin);
            await context.SaveChangesAsync();
            Console.WriteLine($"Default admin user created successfully (Username: {adminUsername}).");
        }
    }
}
