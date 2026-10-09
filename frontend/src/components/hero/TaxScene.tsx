import { Canvas, useFrame } from '@react-three/fiber'
import {
  Component,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ErrorInfo,
  type ReactNode,
} from 'react'
import { CanvasTexture, type Group } from 'three'

function isWebGLAvailable(): boolean {
  try {
    const canvas = document.createElement('canvas')
    return Boolean(
      window.WebGLRenderingContext &&
        (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')),
    )
  } catch {
    return false
  }
}

class SceneErrorBoundary extends Component<
  { children: ReactNode; fallback?: ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.warn('TaxScene WebGL render failed:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? null
    }
    return this.props.children
  }
}

/**
 * Creates a crisp vector-like ₹ texture for the 3D coin face.
 * Zero external font dependency; completely client-side rendered.
 */
function useRupeeTexture() {
  return useMemo(() => {
    if (typeof document === 'undefined') return null
    const canvas = document.createElement('canvas')
    canvas.width = 512
    canvas.height = 512
    const ctx = canvas.getContext('2d')
    if (ctx) {
      ctx.clearRect(0, 0, 512, 512)

      // Outer ring stroke
      ctx.beginPath()
      ctx.arc(256, 256, 224, 0, Math.PI * 2)
      ctx.strokeStyle = 'rgba(16, 185, 129, 0.45)'
      ctx.lineWidth = 14
      ctx.stroke()

      // Inner subtle disk tint
      ctx.beginPath()
      ctx.arc(256, 256, 214, 0, Math.PI * 2)
      ctx.fillStyle = 'rgba(255, 255, 255, 0.06)'
      ctx.fill()

      // ₹ symbol in crisp Space Grotesk / modern sans
      ctx.fillStyle = '#FFFFFF'
      ctx.font = 'bold 260px "Space Grotesk Variable", "Space Grotesk", system-ui, sans-serif'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.shadowColor = 'rgba(16, 185, 129, 0.5)'
      ctx.shadowBlur = 24
      ctx.fillText('₹', 256, 274)
    }

    const texture = new CanvasTexture(canvas)
    texture.needsUpdate = true
    return texture
  }, [])
}

function FloatingFinancialObjects() {
  const rootGroup = useRef<Group>(null)
  const coinGroup = useRef<Group>(null)
  const rupeeTexture = useRupeeTexture()

  useFrame((state, delta) => {
    if (!rootGroup.current) return

    const time = state.clock.elapsedTime
    const dt = Math.min(delta, 0.1)

    // Gentle global idle floating
    rootGroup.current.position.y = Math.sin(time * 0.7) * 0.08

    // Pointer parallax (smooth lerp, disabled on touch devices)
    const isTouch =
      typeof window !== 'undefined' &&
      window.matchMedia('(pointer: coarse)').matches

    if (!isTouch) {
      const targetRotX = -state.pointer.y * 0.14
      const targetRotY = state.pointer.x * 0.22
      rootGroup.current.rotation.x +=
        (targetRotX - rootGroup.current.rotation.x) * Math.min(dt * 2.8, 0.25)
      rootGroup.current.rotation.y +=
        (targetRotY - rootGroup.current.rotation.y) * Math.min(dt * 2.8, 0.25)
    }

    // Secondary coin rotation & bobbing
    if (coinGroup.current) {
      coinGroup.current.rotation.y = time * 0.35
      coinGroup.current.position.y = 0.55 + Math.sin(time * 1.3) * 0.04
    }
  })

  return (
    <group ref={rootGroup}>
      {/* 1. Glass ₹ Coin (Floating top right) */}
      <group position={[1.45, 0.55, -0.4]} ref={coinGroup}>
        {/* Outer Torus Ring */}
        <mesh rotation={[0.15, 0, -0.1]}>
          <torusGeometry args={[0.72, 0.08, 16, 64]} />
          <meshPhysicalMaterial
            color="#34D399"
            metalness={0.15}
            roughness={0.16}
            transmission={0.7}
            thickness={0.5}
            ior={1.52}
            clearcoat={0.3}
          />
        </mesh>
        {/* Inner Glass Disc with ₹ Texture */}
        {rupeeTexture && (
          <mesh rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[0.66, 0.66, 0.04, 36]} />
            <meshPhysicalMaterial
              color="#FFFFFF"
              map={rupeeTexture}
              metalness={0.08}
              roughness={0.18}
              transmission={0.82}
              thickness={0.4}
              ior={1.48}
              transparent
              opacity={0.92}
            />
          </mesh>
        )}
      </group>

      {/* 2. Layered Translucent Document Sheets (Form 16 / Tax Reports - Left) */}
      <group position={[-1.25, -0.15, -0.7]} rotation={[0.12, -0.25, 0.08]}>
        {/* Background Document Sheet */}
        <mesh position={[-0.1, -0.08, -0.1]} rotation={[0, 0, -0.05]}>
          <boxGeometry args={[1.15, 1.48, 0.03]} />
          <meshPhysicalMaterial
            color="#2563EB"
            metalness={0.1}
            roughness={0.25}
            transmission={0.72}
            thickness={0.4}
            ior={1.45}
            transparent
            opacity={0.85}
          />
        </mesh>

        {/* Foreground Primary Document Sheet */}
        <mesh position={[0, 0, 0]}>
          <boxGeometry args={[1.2, 1.55, 0.035]} />
          <meshPhysicalMaterial
            color="#E0EDFF"
            metalness={0.05}
            roughness={0.18}
            transmission={0.84}
            thickness={0.5}
            ior={1.5}
          />
        </mesh>

        {/* Document Content Lines */}
        <mesh position={[-0.15, 0.48, 0.024]}>
          <boxGeometry args={[0.65, 0.05, 0.01]} />
          <meshStandardMaterial color="#2563EB" roughness={0.4} />
        </mesh>
        <mesh position={[-0.05, 0.3, 0.024]}>
          <boxGeometry args={[0.85, 0.04, 0.01]} />
          <meshStandardMaterial color="#94A3B8" roughness={0.5} />
        </mesh>
        <mesh position={[-0.12, 0.14, 0.024]}>
          <boxGeometry args={[0.7, 0.04, 0.01]} />
          <meshStandardMaterial color="#94A3B8" roughness={0.5} />
        </mesh>
        <mesh position={[-0.2, -0.05, 0.024]}>
          <boxGeometry args={[0.55, 0.04, 0.01]} />
          <meshStandardMaterial color="#10B981" roughness={0.4} />
        </mesh>
        <mesh position={[-0.08, -0.22, 0.024]}>
          <boxGeometry args={[0.8, 0.035, 0.01]} />
          <meshStandardMaterial color="#94A3B8" roughness={0.5} />
        </mesh>
      </group>

      {/* 3. Rising Bar-Chart Columns (Old vs New Regime / Savings Growth - Bottom Right) */}
      <group position={[0.75, -0.85, 0.15]} rotation={[0.04, 0.12, -0.06]}>
        {/* Base Glass Pedestal */}
        <mesh position={[0.3, -0.36, 0]}>
          <boxGeometry args={[1.5, 0.05, 0.6]} />
          <meshPhysicalMaterial
            color="#CBD5E1"
            metalness={0.1}
            roughness={0.2}
            transmission={0.75}
            thickness={0.3}
            ior={1.48}
          />
        </mesh>

        {/* Column 1: Baseline Old Regime (Blue-Grey) */}
        <mesh position={[-0.22, -0.08, 0]}>
          <boxGeometry args={[0.26, 0.52, 0.26]} />
          <meshPhysicalMaterial
            color="#3B82F6"
            metalness={0.12}
            roughness={0.2}
            transmission={0.65}
            thickness={0.5}
            ior={1.5}
          />
        </mesh>

        {/* Column 2: Deductions Applied (Trust Blue) */}
        <mesh position={[0.12, 0.12, 0]}>
          <boxGeometry args={[0.26, 0.92, 0.26]} />
          <meshPhysicalMaterial
            color="#2563EB"
            metalness={0.15}
            roughness={0.18}
            transmission={0.68}
            thickness={0.6}
            ior={1.52}
          />
        </mesh>

        {/* Column 3: Maximized Savings New Regime (Vibrant Emerald Glass) */}
        <mesh position={[0.46, 0.34, 0]}>
          <boxGeometry args={[0.26, 1.36, 0.26]} />
          <meshPhysicalMaterial
            color="#10B981"
            metalness={0.2}
            roughness={0.15}
            transmission={0.72}
            thickness={0.7}
            ior={1.54}
            clearcoat={0.3}
          />
        </mesh>
      </group>

      {/* 4. Ambient Floating Nodes & Prisms */}
      <mesh position={[0.05, 1.15, -1.4]} rotation={[0.4, 0.6, 0.2]}>
        <icosahedronGeometry args={[0.18, 1]} />
        <meshPhysicalMaterial
          color="#60A5FA"
          metalness={0.25}
          roughness={0.15}
          transmission={0.75}
          thickness={0.4}
          ior={1.5}
        />
      </mesh>

      <mesh position={[2.25, -0.65, -0.9]} rotation={[0.2, -0.4, 0.3]}>
        <octahedronGeometry args={[0.14, 0]} />
        <meshPhysicalMaterial
          color="#34D399"
          metalness={0.3}
          roughness={0.18}
          transmission={0.7}
          thickness={0.35}
          ior={1.5}
        />
      </mesh>

      <mesh position={[-2.1, 0.85, -1.1]} rotation={[-0.2, 0.3, 0.5]}>
        <icosahedronGeometry args={[0.12, 1]} />
        <meshPhysicalMaterial
          color="#93C5FD"
          metalness={0.2}
          roughness={0.2}
          transmission={0.8}
          thickness={0.3}
          ior={1.48}
        />
      </mesh>
    </group>
  )
}

export function TaxScene() {
  const containerRef = useRef<HTMLDivElement>(null)
  const [inView, setInView] = useState(true)
  const [webGLSupported] = useState(() => isWebGLAvailable())

  // Pause render loop when out of viewport using IntersectionObserver
  useEffect(() => {
    if (!containerRef.current || typeof IntersectionObserver === 'undefined') {
      return
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        setInView(entry.isIntersecting)
      },
      { threshold: 0.05 },
    )

    observer.observe(containerRef.current)
    return () => observer.disconnect()
  }, [])

  if (!webGLSupported) {
    return null
  }

  return (
    <div
      ref={containerRef}
      style={{ width: '100%', height: '100%', position: 'relative' }}
    >
      <SceneErrorBoundary>
        <Canvas
          aria-hidden="true"
          camera={{ position: [0, 0, 5.2], fov: 38 }}
          dpr={[1, 1.5]}
          frameloop={inView ? 'always' : 'never'}
          gl={{
            alpha: true,
            antialias: false,
            powerPreference: 'low-power',
          }}
          onError={(e) => {
            console.warn('Three.js canvas error:', e)
          }}
        >
          {/* Subtle Ambient Light */}
          <ambientLight intensity={1.6} />

          {/* Key Directional Sunlight */}
          <directionalLight position={[4, 5, 4.5]} intensity={2.2} />

          {/* Cool Trust-Blue Key Light */}
          <pointLight
            color="#2563EB"
            intensity={9}
            position={[-3.5, 1.8, 2.5]}
            distance={9}
          />

          {/* Warm Savings-Teal Fill Light */}
          <pointLight
            color="#10B981"
            intensity={8}
            position={[3.5, -1.8, 2]}
            distance={8}
          />

          {/* Floating Financial Geometry */}
          <FloatingFinancialObjects />
        </Canvas>
      </SceneErrorBoundary>
    </div>
  )
}