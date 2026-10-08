import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { useRef } from 'react'
import type { Group } from 'three'

function FloatingObjects() {
  const group = useRef<Group>(null)
  const { pointer } = useThree()

  useFrame((state, delta) => {
    if (!group.current) return
    group.current.rotation.y +=
      (pointer.x * 0.12 - group.current.rotation.y) * Math.min(delta * 1.5, 1)
    group.current.rotation.x +=
      (-pointer.y * 0.08 - group.current.rotation.x) * Math.min(delta * 1.5, 1)
    group.current.position.y = Math.sin(state.clock.elapsedTime * 0.5) * 0.06
  })

  return (
    <group ref={group}>
      <mesh position={[1.5, 0.55, -0.6]} rotation={[0.15, 0.3, -0.1]}>
        <torusGeometry args={[0.72, 0.09, 14, 72]} />
        <meshStandardMaterial color="#44d9a0" metalness={0.62} roughness={0.25} />
      </mesh>
      <mesh position={[-1.25, -0.3, -1]} rotation={[0.08, -0.28, 0.12]}>
        <boxGeometry args={[1.15, 1.45, 0.12]} />
        <meshStandardMaterial color="#3656e8" metalness={0.26} roughness={0.3} />
      </mesh>
      <mesh position={[-1.25, -0.3, -0.91]}>
        <boxGeometry args={[0.68, 0.05, 0.025]} />
        <meshStandardMaterial color="#dce5ff" roughness={0.5} />
      </mesh>
      <mesh position={[0.45, -0.9, 0.25]} rotation={[0, 0.1, -0.08]}>
        <boxGeometry args={[1.3, 0.62, 0.12]} />
        <meshStandardMaterial color="#ffc765" metalness={0.3} roughness={0.3} />
      </mesh>
      <mesh position={[0.45, -0.9, 0.33]}>
        <boxGeometry args={[0.72, 0.055, 0.025]} />
        <meshStandardMaterial color="#fff0ce" roughness={0.5} />
      </mesh>
      <mesh position={[0, 0.9, -1.6]}>
        <icosahedronGeometry args={[0.16, 1]} />
        <meshStandardMaterial color="#7b92ff" metalness={0.65} roughness={0.22} />
      </mesh>
      <mesh position={[2.2, -0.85, -1.2]}>
        <icosahedronGeometry args={[0.1, 1]} />
        <meshStandardMaterial color="#69e6b2" metalness={0.55} roughness={0.25} />
      </mesh>
    </group>
  )
}

export function TaxScene() {
  return (
    <Canvas
      aria-hidden="true"
      camera={{ position: [0, 0, 5.2], fov: 40 }}
      dpr={[1, 1.3]}
      gl={{ alpha: true, antialias: false, powerPreference: 'low-power' }}
    >
      <ambientLight intensity={2.2} />
      <directionalLight position={[3, 4, 5]} intensity={2.4} />
      <pointLight color="#5480ff" intensity={12} position={[-3, -1, 3]} />
      <FloatingObjects />
    </Canvas>
  )
}
