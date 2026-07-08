using System.Collections.Concurrent;

namespace IoTBackend.Services
{
    public static class SessionManager
    {
        public class UserSession
        {
            public string Username { get; set; } = string.Empty;
            public string Role { get; set; } = string.Empty;
            public DateTimeOffset ExpiresAtUtc { get; set; }
        }

        private static readonly ConcurrentDictionary<string, UserSession> ActiveSessions = new();
        private static readonly TimeSpan DefaultSessionLifetime = TimeSpan.FromHours(8);

        public static string CreateSession(string username, string role)
        {
            return CreateSession(username, role, DefaultSessionLifetime, out _);
        }

        public static string CreateSession(string username, string role, TimeSpan lifetime, out DateTimeOffset expiresAtUtc)
        {
            if (lifetime <= TimeSpan.Zero)
            {
                lifetime = DefaultSessionLifetime;
            }

            var token = Guid.NewGuid().ToString("N");
            expiresAtUtc = DateTimeOffset.UtcNow.Add(lifetime);
            ActiveSessions[token] = new UserSession
            {
                Username = username,
                Role = role,
                ExpiresAtUtc = expiresAtUtc
            };
            return token;
        }

        public static bool IsValidToken(string token)
        {
            return TryGetSession(token, out _);
        }

        public static string? GetUsername(string token)
        {
            if (TryGetSession(token, out var session))
            {
                return session.Username;
            }
            return null;
        }

        public static string? GetRole(string token)
        {
            if (TryGetSession(token, out var session))
            {
                return session.Role;
            }
            return null;
        }

        public static DateTimeOffset? GetExpiresAtUtc(string token)
        {
            return TryGetSession(token, out var session) ? session.ExpiresAtUtc : null;
        }

        public static bool TryGetSession(string? token, out UserSession session)
        {
            session = new UserSession();
            if (string.IsNullOrWhiteSpace(token))
            {
                return false;
            }

            if (!ActiveSessions.TryGetValue(token, out var activeSession))
            {
                return false;
            }

            if (activeSession.ExpiresAtUtc <= DateTimeOffset.UtcNow)
            {
                RemoveSession(token);
                return false;
            }

            session = activeSession;
            return true;
        }

        public static bool TryGetBearerToken(string? authHeader, out string token)
        {
            token = string.Empty;
            if (string.IsNullOrWhiteSpace(authHeader) ||
                !authHeader.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase))
            {
                return false;
            }

            token = authHeader.Substring("Bearer ".Length).Trim();
            return !string.IsNullOrWhiteSpace(token);
        }

        public static void RemoveSession(string token)
        {
            ActiveSessions.TryRemove(token, out _);
        }
    }
}
