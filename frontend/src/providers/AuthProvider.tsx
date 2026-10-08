import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { User } from '@supabase/supabase-js'
import { setApiAccessTokenProvider } from '../lib/api'
import { supabase, supabaseConfigured } from '../lib/supabase'
import { AuthContext } from './auth-context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(supabaseConfigured)
  const [authError, setAuthError] = useState<string | null>(null)

  useEffect(() => {
    if (!supabase) return
    let active = true
    const { data } = supabase.auth.onAuthStateChange((_event, session) => {
      if (active) setUser(session?.user ?? null)
    })
    void supabase.auth.getSession().then(({ data: sessionData, error }) => {
      if (active) {
        setUser(sessionData.session?.user ?? null)
        setAuthError(error?.message ?? null)
        setLoading(false)
      }
    }).catch((error: unknown) => {
      if (active) {
        setAuthError(error instanceof Error ? error.message : 'Unable to load your session.')
        setLoading(false)
      }
    })
    return () => {
      active = false
      data.subscription.unsubscribe()
    }
  }, [])

  useEffect(() => {
    setApiAccessTokenProvider(async () => {
      if (!supabase) return null
      const { data, error } = await supabase.auth.getSession()
      if (error) throw error
      return data.session?.access_token ?? null
    })
  }, [])

  const signIn = useCallback(async (email: string, password: string) => {
    if (!supabase) throw new Error('Supabase authentication is not configured.')
    const { data, error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) throw error
    setUser(data.user)
  }, [])

  const signUp = useCallback(async (email: string, password: string) => {
    if (!supabase) throw new Error('Supabase authentication is not configured.')
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: { emailRedirectTo: `${window.location.origin}/login` },
    })
    if (error) throw error
    if (data.user && data.session) setUser(data.user)
    return data.session !== null
  }, [])

  const signOut = useCallback(async () => {
    if (!supabase) throw new Error('Supabase authentication is not configured.')
    const { error } = await supabase.auth.signOut()
    if (error) throw error
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({
      user,
      loading,
      configured: supabaseConfigured,
      authError,
      signIn,
      signUp,
      signOut,
    }),
    [user, loading, authError, signIn, signUp, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
