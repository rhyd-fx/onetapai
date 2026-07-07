"use client";

import { Suspense, useEffect, useState, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, MeshDistortMaterial, Icosahedron, OrbitControls, useTexture } from '@react-three/drei';
import * as THREE from 'three';

function RotatingGrid() {
  const ref = useRef<THREE.GridHelper>(null);
  useFrame((state) => {
    if (ref.current) {
      ref.current.rotation.y = state.clock.getElapsedTime() * 0.15;
    }
  });
  return <gridHelper ref={ref} args={[2.5, 12, '#22d3ee', '#1e293b']} position={[0, -1.0, 0]} />;
}

function ScanningRing() {
  const ref = useRef<THREE.Mesh>(null);
  useFrame((state) => {
    if (ref.current) {
      // Oscilate vertically between -1.0 and 1.3
      ref.current.position.y = -1.0 + (Math.sin(state.clock.getElapsedTime() * 1.2) + 1) * 1.15;
    }
  });
  return (
    <mesh ref={ref} rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.0, 0]}>
      <ringGeometry args={[0.95, 1.0, 32]} />
      <meshBasicMaterial color="#22d3ee" transparent opacity={0.6} side={2} />
    </mesh>
  );
}

function AgentHologram({ url }: { url: string }) {
  const texture = useTexture(url);
  const ref = useRef<THREE.Group>(null);

  useFrame((state) => {
    if (ref.current) {
      ref.current.quaternion.copy(state.camera.quaternion);
    }
  });

  return (
    <group ref={ref} position={[0, 0.15, 0]}>
      {/* Holographic Cyan Parallax Back-glitch shadow */}
      <mesh position={[0, 0, -0.08]} scale={[1.8, 2.4, 1]}>
        <planeGeometry args={[1, 1]} />
        <meshBasicMaterial 
          map={texture} 
          transparent={true} 
          color="#22d3ee"
          opacity={0.3}
          depthWrite={false}
          side={2}
        />
      </mesh>

      {/* Main Full-Color Agent portrait (always faces camera via quaternion copy) */}
      <mesh position={[0, 0, 0]} scale={[1.8, 2.4, 1]}>
        <planeGeometry args={[1, 1]} />
        <meshBasicMaterial 
          map={texture} 
          transparent={true} 
          depthWrite={false}
          side={2}
        />
      </mesh>

      {/* Holographic Red Parallax Back-glitch shadow */}
      <mesh position={[0, 0, -0.16]} scale={[1.8, 2.4, 1]}>
        <planeGeometry args={[1, 1]} />
        <meshBasicMaterial 
          map={texture} 
          transparent={true} 
          color="#ff4655"
          opacity={0.15}
          depthWrite={false}
          side={2}
        />
      </mesh>
    </group>
  );
}

function HologramScene({ url, agent }: { url: string | null; agent: string }) {
  const isFlex = agent.toLowerCase() === 'flex' || !url;

  return (
    <>
      <ambientLight intensity={0.7} />
      <pointLight position={[5, 5, 5]} intensity={1.8} color="#ff4655" />
      <pointLight position={[-5, 3, -5]} intensity={1.2} color="#22d3ee" />
      
      <Suspense fallback={null}>
        {isFlex ? (
          <Float speed={1.5} rotationIntensity={1.2} floatIntensity={1.2}>
            <Icosahedron args={[1.1, 6]}>
              <MeshDistortMaterial
                color="#ff4655"
                emissive="#4a0d13"
                emissiveIntensity={0.6}
                roughness={0.12}
                metalness={0.65}
                distort={0.4}
                speed={1.8}
              />
            </Icosahedron>
          </Float>
        ) : (
          <>
            <AgentHologram url={url} />
            <RotatingGrid />
            <ScanningRing />
            
            {/* Base Ring pad */}
            <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.01, 0]}>
              <ringGeometry args={[1.05, 1.15, 32]} />
              <meshBasicMaterial color="#ff4655" transparent opacity={0.4} side={2} />
            </mesh>
          </>
        )}
      </Suspense>

      <OrbitControls 
        enableZoom={false} 
        enablePan={false} 
        autoRotate={true}
        autoRotateSpeed={0.8} 
      />
    </>
  );
}

export default function AgentHero({ agent }: { agent: string }) {
  const [portraitUrl, setPortraitUrl] = useState<string | null>(null);

  useEffect(() => {
    if (agent.toLowerCase() === 'flex') return;

    fetch('https://valorant-api.com/v1/agents?isPlayableCharacter=true')
      .then((res) => res.json())
      .then((res) => {
        if (res?.data) {
          const matching = res.data.find(
            (a: any) => a.displayName.toLowerCase() === agent.toLowerCase()
          );
          if (matching?.fullPortrait) {
            setPortraitUrl(matching.fullPortrait);
          }
        }
      })
      .catch((err) => console.error('Error fetching agent portrait for 3D visual:', err));
  }, [agent]);

  return (
    <div className="relative h-full min-h-[240px] w-full cursor-grab active:cursor-grabbing">
      <Canvas camera={{ position: [0, 0, 4.2], fov: 42 }} dpr={[1, 2]}>
        <HologramScene url={portraitUrl} agent={agent} />
      </Canvas>

      {/* Neon vignette + label overlay */}
      <div className="pointer-events-none absolute inset-0 rounded-2xl ring-1 ring-brand-red/20 [box-shadow:inset_0_0_60px_-20px_rgba(255,70,85,0.5)]" />
      <div className="pointer-events-none absolute left-4 top-4 select-none">
        <div className="text-[10px] font-semibold tracking-[0.2em] text-brand-blue/80">TOP AGENT</div>
        <div className="text-lg font-bold tracking-wide text-white drop-shadow-[0_0_10px_rgba(255,70,85,0.6)] uppercase">
          {agent}
        </div>
      </div>
      <div className="pointer-events-none absolute right-4 bottom-4 select-none text-[8px] uppercase tracking-widest text-muted/60 font-bold">
        Drag to Rotate 360°
      </div>
    </div>
  );
}
