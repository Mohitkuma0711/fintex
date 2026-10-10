import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import type { User } from '@supabase/supabase-js'
import { clearApiResponseCache, setApiAccessTokenProvider } from '../lib/api'
import { mintDevAuthToken } from '../lib/dev-auth-token'
import { supabase } from '../lib/supabase'
import { AuthContext, type AuthContextValue } from './auth-context'

export { useAuth } from './useAuth'

const useDevAuthTokens = import.meta.env.VITE_AUTH_TEST_MODE === 'true'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const userRef = useRef<User | null>(user)
  userRef.current = user

  useEffect(() => {
    setApiAccessTokenProvider(async () => {
      if (useDevAuthTokens && userRef.current) {
        return mintDevAuthToken(userRef.current.id)
      }
      const { data } = await supabase.auth.getSession()
      return data.session?.access_token ?? null
    })

    void supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null)
      setLoading(false)
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null)
      setLoading(false)
      clearApiResponseCache()
    })

    return () => {
      subscription.unsubscribe()
      setApiAccessTokenProvider(async () => null)
    }
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      async signInWithEmail(email, password) {
        const { error } = await supabase.auth.signInWithPassword({
          email,
          password,
        })
        if (error) throw error
      },
      async signUpWithEmail(email, password) {
        const { error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            emailRedirectTo: `${window.location.origin}/upload`,
          },
        })
        if (error) throw error
      },
      async signInWithGoogle() {
        const { error } = await supabase.auth.signInWithOAuth({
          provider: 'google',
          options: {
            redirectTo: `${window.location.origin}/upload`,
          },
        })
        if (error) {
          if (/provider is not enabled/i.test(error.message)) {
            throw new Error(
              'Google sign-in is not enabled for this Supabase project. Enable Google in Supabase Auth → Providers, then add its Google OAuth client ID and secret.',
            )
          }
          throw error
        }
      },
      async signOutUser() {
        const { error } = await supabase.auth.signOut()
        if (error) throw error
        setUser(null)
      },
    }),
    [loading, user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
