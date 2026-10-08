const inrFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
})

export function formatINR(value: number): string {
  if (!Number.isFinite(value)) throw new RangeError('INR value must be finite')
  return inrFormatter.format(value)
}

export function formatINRExact(value: string): string {
  if (value.length > 128) throw new RangeError('INR value is too large to format')
  const match = /^(-?)(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?$/.exec(value)
  if (!match) throw new RangeError('INR value must be a plain decimal string')
  const [, sign, whole, fractional = '', exponentText = '0'] = match
  const digits = `${whole}${fractional}`
  const exponent = Number(exponentText)
  if (!Number.isSafeInteger(exponent) || Math.abs(exponent) > 100) {
    throw new RangeError('INR value exponent is outside the supported range')
  }
  const decimalPosition = whole.length + exponent
  const integer = decimalPosition <= 0
    ? '0'
    : decimalPosition >= digits.length
      ? `${digits}${'0'.repeat(decimalPosition - digits.length)}`
      : digits.slice(0, decimalPosition)
  const fraction = decimalPosition <= 0
    ? `${'0'.repeat(-decimalPosition)}${digits}`
    : decimalPosition >= digits.length
      ? ''
      : digits.slice(decimalPosition)
  const groupedInteger = BigInt(integer).toLocaleString('en-IN')
  return `${sign ? '-₹' : '₹'}${groupedInteger}${fraction ? `.${fraction}` : ''}`
}
