using Microsoft.AspNetCore.SignalR;

namespace IoTBackend.Hubs
{
    public class FactoryHub : Hub
    {
        public async Task SendTemperatureUpdateAsync(decimal temperature)
        {
            await Clients.All.SendAsync("ReceiveTemperatureUpdate", temperature);
        }

        public async Task SendSmokeUpdateAsync(bool smoke)
        {
            await Clients.All.SendAsync("ReceiveSmokeUpdate", smoke);
        }

        public async Task SendWeightUpdateAsync(decimal weight)
        {
            await Clients.All.SendAsync("ReceiveWeightUpdate", weight);
        }

        public async Task SendProductNumberUpdateAsync(string productNumber)
        {
            await Clients.All.SendAsync("ReceiveProductNumberUpdate", productNumber);
        }
    }
}
