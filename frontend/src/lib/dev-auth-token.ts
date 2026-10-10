const TEST_SECRET = 'super-secret-jwt-token-with-at-least-32-chars-long'
const TOKEN_TTL_SECONDS = 3600

function base64UrlEncode(bytes: Uint8Array): string {
  let binary = ''
  for (const byte of bytes) binary += String.fromCharCode(byte)
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

export async function mintDevAuthToken(uid: string): Promise<string> {
  const encoder = new TextEncoder()
  const now = Math.floor(Date.now() / 1000)
  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://demo.supabase.co'
  const issuer = `${supabaseUrl.replace(/\/+$/, '')}/auth/v1`
  const header = base64UrlEncode(
    encoder.encode(JSON.stringify({ alg: 'HS256', typ: 'JWT' })),
  )
  const payload = base64UrlEncode(
    encoder.encode(
      JSON.stringify({
        sub: uid,
        role: 'authenticated',
        iss: issuer,
        aud: 'authenticated',
        iat: now,
        exp: now + TOKEN_TTL_SECONDS,
      }),
    ),
  )
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(TEST_SECRET),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  )
  const signature = await crypto.subtle.sign(
    'HMAC',
    key,
    encoder.encode(`${header}.${payload}`),
  )
  return `${header}.${payload}.${base64UrlEncode(new Uint8Array(signature))}`
}
