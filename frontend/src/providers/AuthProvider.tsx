import {
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import {
  GoogleAuthProvider,
  browserLocalPersistence,
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  setPersistence,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut,
  type User,
} from 'firebase/auth'
import { clearApiResponseCache, setApiAccessTokenProvider } from '../lib/api'
import { mintDevAuthToken } from '../lib/dev-auth-token'
import { auth } from '../lib/firebase'
import { AuthContext, type AuthContextValue } from './auth-context'

export { useAuth } from './useAuth'

const useDevAuthTokens = import.meta.env.VITE_AUTH_TEST_MODE === 'true'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    void setPersistence(auth, browserLocalPersistence)
    setApiAccessTokenProvider(async () => {
      const current = auth.currentUser
      if (!current) return null
      if (useDevAuthTokens) return mintDevAuthToken(current.uid)
      return current.getIdToken()
    })
    const unsubscribe = onAuthStateChanged(auth, (nextUser) => {
      setUser(nextUser)
      setLoading(false)
      clearApiResponseCache()
    })
    return () => {
      unsubscribe()
      setApiAccessTokenProvider(async () => null)
    }
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      async signInWithEmail(email, password) {
        await signInWithEmailAndPassword(auth, email, password)
      },
      async signUpWithEmail(email, password) {
        await createUserWithEmailAndPassword(auth, email, password)
      },
      async signInWithGoogle() {
        await signInWithPopup(auth, new GoogleAuthProvider())
      },
      async signOutUser() {
        await signOut(auth)
      },
    }),
    [loading, user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
