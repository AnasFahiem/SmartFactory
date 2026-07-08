using System.ComponentModel.DataAnnotations;

namespace IoTBackend.Models
{
    public class Product
    {
        public int Id { get; set; }

        [Required]
        [MaxLength(128)]
        public string ProductNumber { get; set; } = string.Empty;

        public decimal? Weight { get; set; }
    }
}
