/**
 * Format price to Vietnamese currency with "000" suffix
 * @param price - Price value (in smallest unit, e.g., 50 for 50,000đ)
 * @returns Formatted price string (e.g., "50,000đ")
 */
export function formatPrice(price: number): string {
  // Multiply by 1000 to add "000" suffix
  const priceInVND = price * 1000;
  return `${priceInVND.toLocaleString('vi-VN')}đ`;
}

/**
 * Format price range to Vietnamese currency format
 * If price range is like "~50", format to "~50000đ"
 * If price range is "$", "$$", "$$$", keep as is
 * @param priceRange - Price range string (e.g., "~50", "$", "$$", "$$$")
 * @returns Formatted price range string
 */
export function formatPriceRange(priceRange: string): string {
  // Check if price range starts with "~" and contains a number
  const tildeMatch = priceRange.match(/^~(\d+)$/);
  if (tildeMatch) {
    const number = parseInt(tildeMatch[1], 10);
    const priceInVND = number * 1000;
    return `~${priceInVND.toLocaleString('vi-VN')}đ`;
  }
  
  // If it's a standard price range symbol, return as is
  return priceRange;
}

