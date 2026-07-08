using System.ComponentModel.DataAnnotations;

namespace IoTBackend.Models
{
    public class ProductScan
    {
        public int Id { get; set; }
        
        [Required]
        public string ProductNumber { get; set; } = string.Empty;
        
        public decimal ActualWeight { get; set; }
        
        public DateTime ScanTime { get; set; } = DateTime.UtcNow;
    }
}
