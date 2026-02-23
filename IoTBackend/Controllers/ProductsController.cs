using Microsoft.AspNetCore.Mvc;
using IoTBackend.Data;
using IoTBackend.Models;

namespace IoTBackend.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class ProductsController : ControllerBase
    {
        private readonly AppDbContext _dbContext;
        private readonly ILogger<ProductsController> _logger;

        public ProductsController(AppDbContext dbContext, ILogger<ProductsController> logger)
        {
            _dbContext = dbContext;
            _logger = logger;
        }

        [HttpGet]
        public ActionResult<IEnumerable<Product>> GetProducts()
        {
            var products = _dbContext.Products.ToList();
            return Ok(products);
        }

        [HttpGet("latest")]
        public ActionResult<Product> GetLatestProduct()
        {
            var latestProduct = _dbContext.Products
                .OrderByDescending(p => p.Id)
                .FirstOrDefault();

            if (latestProduct == null)
                return NotFound();

            return Ok(latestProduct);
        }
    }
}
