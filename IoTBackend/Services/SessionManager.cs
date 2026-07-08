using System.Collections.Concurrent;

namespace IoTBackend.Services
{
    public static class SessionManager
    {
        public class UserSession
        {
            public string Username { get; set; } = string.Empty;
            public string Role { get; set; } = string.Empty;
        }

        private static readonly ConcurrentDictionary<string, UserSession> ActiveSessions = new();

        public static string CreateSession(string username, string role)
        {
            var token = Guid.NewGuid().ToString("N");
            ActiveSessions[token] = new UserSession { Username = username, Role = role };
            return token;
        }

        public static bool IsValidToken(string token)
        {
            return ActiveSessions.ContainsKey(token);
        }

        public static string? GetUsername(string token)
        {
            if (ActiveSessions.TryGetValue(token, out var session))
            {
                return session.Username;
            }
            return null;
        }

        public static string? GetRole(string token)
        {
            if (ActiveSessions.TryGetValue(token, out var session))
            {
                return session.Role;
            }
            return null;
        }

        public static void RemoveSession(string token)
        {
            ActiveSessions.TryRemove(token, out _);
        }
    }
}
