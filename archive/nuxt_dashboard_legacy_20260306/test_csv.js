
const pricesStore = {
  forecast: Array.from({ length: 24 }, (_, i) => ({
    price: 10 + Math.sin(i / 3) * 5,
    timestamp: new Date()
  })),
  todayAvg: 10
};

const exportPriceData = () => {
  const now = new Date()
  const dateStr = now.toISOString().split('T')[0]
  const filename = `price-history-${dateStr}.csv`
  
  // Get the last 8 hours of price data
  const priceData = pricesStore.forecast.slice(0, 8)
  
  // Build CSV header
  let csv = 'Hour,Price(₴/kWh),Status,vs Average,Action\n'
  
  // Build CSV rows
  priceData.forEach((price, idx) => {
    const hour = (new Date().getHours() + idx) % 24
    const priceValue = price.price.toFixed(2)
    
    // Determine status
    let status = 'Normal'
    if (price.price > (pricesStore.todayAvg * 1.15)) {
      status = 'Peak'
    } else if (price.price < (pricesStore.todayAvg * 0.85)) {
      status = 'Off-Peak'
    }
    
    // Calculate vs Average percentage
    const vsAvg = ((price.price - pricesStore.todayAvg) / pricesStore.todayAvg * 100).toFixed(0)
    
    // Determine action
    let action = '-'
    if (price.price < (pricesStore.todayAvg * 0.85)) {
      action = 'Buy'
    } else if (price.price > (pricesStore.todayAvg * 1.15)) {
      action = 'Sell'
    }
    
    csv += `${hour}:00,${priceValue},${status},${vsAvg}%,${action}\n`
  })
  
  console.log('Filename:', filename);
  console.log('CSV Content:\n' + csv);
}

exportPriceData();
