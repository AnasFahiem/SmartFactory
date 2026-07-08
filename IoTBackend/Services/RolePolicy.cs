namespace IoTBackend.Services
{
    public static class RolePolicy
    {
        private static readonly string[] AllowedRoles = { "User", "Manager", "Admin" };

        public static bool TryNormalize(string? requestedRole, out string normalizedRole)
        {
            normalizedRole = string.Empty;
            if (string.IsNullOrWhiteSpace(requestedRole))
            {
                return false;
            }

            var match = AllowedRoles.FirstOrDefault(role =>
                string.Equals(role, requestedRole.Trim(), StringComparison.OrdinalIgnoreCase));

            if (match == null)
            {
                return false;
            }

            normalizedRole = match;
            return true;
        }
    }
}
