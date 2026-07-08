using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using IoTBackend.Data;
using IoTBackend.Models;
using IoTBackend.Attributes;

namespace IoTBackend.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    [CustomAuthorize]
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

        [HttpGet("analytics/{productNumber}")]
        public async Task<ActionResult> GetProductAnalytics(string productNumber)
        {
            var product = _dbContext.Products.FirstOrDefault(p => p.ProductNumber == productNumber);
            if (product == null)
                return NotFound(new { message = "Product not found." });

            var scans = _dbContext.ProductScans
                .Where(s => s.ProductNumber == productNumber)
                .OrderByDescending(s => s.ScanTime)
                .ToList();
            var totalScans = scans.Count;
            decimal averageActualWeight = 0;
            decimal variance = 0;

            if (totalScans > 0)
            {
                averageActualWeight = scans.Average(s => s.ActualWeight);
                if (product.Weight.HasValue)
                {
                    variance = averageActualWeight - product.Weight.Value;
                }
            }

            var scanRows = scans.Select((scan, index) =>
            {
                decimal? differenceFromIdeal = product.Weight.HasValue
                    ? scan.ActualWeight - product.Weight.Value
                    : null;
                bool? isWithinTolerance = product.Weight.HasValue
                    ? Math.Abs(scan.ActualWeight - product.Weight.Value) <= product.Weight.Value * 0.10m
                    : null;

                return new
                {
                    Sequence = totalScans - index,
                    scan.Id,
                    scan.ProductNumber,
                    scan.ActualWeight,
                    scan.ScanTime,
                    DifferenceFromIdeal = differenceFromIdeal,
                    IsWithinTolerance = isWithinTolerance
                };
            });

            return Ok(new
            {
                ProductNumber = product.ProductNumber,
                IdealWeight = product.Weight,
                AverageActualWeight = averageActualWeight,
                Variance = variance,
                TotalScans = totalScans,
                Scans = scanRows
            });
        }

        [HttpDelete("analytics/{productNumber}/scans")]
        [CustomAuthorize(Roles = "Manager,Admin")]
        public async Task<IActionResult> ResetProductScans(string productNumber)
        {
            if (string.IsNullOrWhiteSpace(productNumber))
            {
                return BadRequest(new { message = "Product code is required." });
            }

            var normalizedProductNumber = productNumber.Trim();
            var productExists = await _dbContext.Products.AnyAsync(p => p.ProductNumber == normalizedProductNumber);
            if (!productExists)
            {
                return NotFound(new { message = "Product not found." });
            }

            var scans = await _dbContext.ProductScans
                .Where(scan => scan.ProductNumber == normalizedProductNumber)
                .ToListAsync();

            var deletedCount = scans.Count;
            if (deletedCount > 0)
            {
                _dbContext.ProductScans.RemoveRange(scans);
                await _dbContext.SaveChangesAsync();
            }

            _logger.LogInformation(
                "Reset {DeletedCount} product scans for product {ProductNumber}.",
                deletedCount,
                normalizedProductNumber);

            return Ok(new
            {
                message = "Product scans reset successfully.",
                productNumber = normalizedProductNumber,
                deletedCount
            });
        }

        [HttpPost]
        public async Task<ActionResult<Product>> CreateProduct([FromBody] Product productDto)
        {
            if (productDto == null || string.IsNullOrWhiteSpace(productDto.ProductNumber))
            {
                return BadRequest(new { message = "Product code is required." });
            }

            var newProduct = new Product
            {
                ProductNumber = productDto.ProductNumber,
                Weight = productDto.Weight
            };

            _dbContext.Products.Add(newProduct);
            await _dbContext.SaveChangesAsync();

            return Ok(newProduct);
        }

        [HttpPut("{id}")]
        [CustomAuthorize(Roles = "Manager,Admin")]
        public async Task<IActionResult> UpdateProduct(int id, [FromBody] Product productDto)
        {
            var product = await _dbContext.Products.FindAsync(id);
            if (product == null)
                return NotFound(new { message = "Product not found." });

            if (string.IsNullOrWhiteSpace(productDto.ProductNumber))
            {
                return BadRequest(new { message = "Product code is required." });
            }

            product.ProductNumber = productDto.ProductNumber;
            product.Weight = productDto.Weight;

            await _dbContext.SaveChangesAsync();
            return Ok(new { message = "Product updated successfully.", product });
        }

        [HttpDelete("{id}")]
        [CustomAuthorize(Roles = "Manager,Admin")]
        public async Task<IActionResult> DeleteProduct(int id)
        {
            var product = await _dbContext.Products.FindAsync(id);
            if (product == null)
                return NotFound(new { message = "Product not found." });

            _dbContext.Products.Remove(product);
            await _dbContext.SaveChangesAsync();

            return Ok(new { message = "Product deleted successfully." });
        }
    }
}