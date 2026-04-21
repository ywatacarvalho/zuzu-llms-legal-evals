export const calcDailyReturns = (prices: number[]): number[] => {
  const rets: number[] = [];
  for (let i = 1; i < prices.length; i++) {
    rets.push(prices[i] / prices[i - 1] - 1);
  }
  return rets;
};

export const mean = (arr: number[]): number =>
  arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;

export const stdDev = (arr: number[]): number => {
  if (arr.length <= 1) return 0;
  const m = mean(arr);
  return Math.sqrt(arr.reduce((sq, n) => sq + Math.pow(n - m, 2), 0) / (arr.length - 1));
};

export const calculateMaxDrawdown = (prices: number[]): number => {
  let maxDD = 0;
  let peak = prices[0];
  for (let i = 1; i < prices.length; i++) {
    if (prices[i] > peak) peak = prices[i];
    const dd = (peak - prices[i]) / peak;
    if (dd > maxDD) maxDD = dd;
  }
  return -maxDD;
};
