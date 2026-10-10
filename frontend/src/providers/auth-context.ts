import { createContext } from 'react'
import type { User } from '@supabase/supabase-js'

export interface AuthContextValue {
  user: User | null
  loading: boolean
  signInWithEmail: (email: string, password: string) => Promise<void>
  signUpWithEmail: (email: string, password: string) => Promise<void>
  signInWithGoogle: () => Promise<void>
  signOutUser: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)
