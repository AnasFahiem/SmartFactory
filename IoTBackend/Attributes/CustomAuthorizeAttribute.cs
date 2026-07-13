using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Filters;
using IoTBackend.Services;

namespace IoTBackend.Attributes
{
    [AttributeUsage(AttributeTargets.Class | AttributeTargets.Method)]
    public class CustomAuthorizeAttribute : Attribute, IAuthorizationFilter
    {
        public string? Roles { get; set; }

        public void OnAuthorization(AuthorizationFilterContext context)
        {
            // Allow anonymous access if endpoint has [AllowAnonymous]
            var hasAllowAnonymous = context.ActionDescriptor.EndpointMetadata
                .Any(em => em.GetType() == typeof(Microsoft.AspNetCore.Authorization.AllowAnonymousAttribute));
            if (hasAllowAnonymous)
                return;

            var authHeader = context.HttpContext.Request.Headers["Authorization"].ToString();
            if (!SessionManager.TryGetBearerToken(authHeader, out var token))
            {
                context.Result = new UnauthorizedObjectResult(new { message = "Unauthorized. Missing or invalid Authorization header." });
                return;
            }

            if (!SessionManager.IsValidToken(token))
            {
                context.Result = new UnauthorizedObjectResult(new { message = "Unauthorized. Token is invalid or expired." });
                return;
            }

            if (!string.IsNullOrEmpty(Roles))
            {
                var userRole = SessionManager.GetRole(token);
                var allowedRoles = Roles.Split(',').Select(r => r.Trim()).ToList();
                if (userRole == null || !allowedRoles.Contains(userRole, StringComparer.OrdinalIgnoreCase))
                {
                    context.Result = new ObjectResult(new { message = "Forbidden. Insufficient permissions." }) { StatusCode = 403 };
                    return;
                }
            }
        }
    }
}
