import { useRef, useMemo, useEffect } from 'react';
import * as THREE from 'three';

export function Enhanced3DBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });

    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    camera.position.z = 20;

    // Ambient and point lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);
    
    const pointLight1 = new THREE.PointLight(0xffffff, 1);
    pointLight1.position.set(10, 10, 10);
    scene.add(pointLight1);
    
    const pointLight2 = new THREE.PointLight(0xC8001E, 0.5);
    pointLight2.position.set(-10, -10, -10);
    scene.add(pointLight2);

    // Blood cell particles
    const particlesCount = 30;
    const particles: THREE.Mesh[] = [];
    
    for (let i = 0; i < particlesCount; i++) {
      const geometry = new THREE.SphereGeometry(Math.random() * 0.5 + 0.3, 16, 16);
      const material = new THREE.MeshStandardMaterial({
        color: 0xC8001E,
        emissive: 0xC8001E,
        emissiveIntensity: 0.2,
        transparent: true,
        opacity: 0.6,
        roughness: 0.3,
        metalness: 0.8,
      });
      const particle = new THREE.Mesh(geometry, material);
      particle.position.set(
        (Math.random() - 0.5) * 50,
        (Math.random() - 0.5) * 50,
        (Math.random() - 0.5) * 30
      );
      particle.userData.speed = Math.random() * 0.02 + 0.01;
      particle.userData.offset = Math.random() * Math.PI * 2;
      scene.add(particle);
      particles.push(particle);
    }

    // DNA Helix
    const helixGroup = new THREE.Group();
    const turns = 3;
    const pointsPerTurn = 20;
    
    for (let i = 0; i < turns * pointsPerTurn; i++) {
      const t = (i / pointsPerTurn) * Math.PI * 2;
      const y = (i / (turns * pointsPerTurn)) * 20 - 10;
      
      const geometry1 = new THREE.SphereGeometry(0.15, 8, 8);
      const material1 = new THREE.MeshStandardMaterial({
        color: 0xE8294A,
        emissive: 0xE8294A,
        emissiveIntensity: 0.3,
      });
      const sphere1 = new THREE.Mesh(geometry1, material1);
      sphere1.position.set(Math.cos(t) * 3, y, Math.sin(t) * 3);
      helixGroup.add(sphere1);
      
      const sphere2 = new THREE.Mesh(geometry1.clone(), material1.clone());
      sphere2.position.set(Math.cos(t + Math.PI) * 3, y, Math.sin(t + Math.PI) * 3);
      helixGroup.add(sphere2);
    }
    
    helixGroup.position.set(15, 0, -10);
    scene.add(helixGroup);

    // Interactive mesh
    const torusGeometry = new THREE.TorusKnotGeometry(2, 0.4, 100, 16);
    const torusMaterial = new THREE.MeshStandardMaterial({
      color: 0x7C3AED,
      emissive: 0x7C3AED,
      emissiveIntensity: 0.2,
      wireframe: true,
      transparent: true,
      opacity: 0.4,
    });
    const torusMesh = new THREE.Mesh(torusGeometry, torusMaterial);
    torusMesh.position.set(-10, 0, -5);
    scene.add(torusMesh);

    // Mouse tracking
    const mousePosition = { x: 0, y: 0 };
    const handleMouseMove = (e: MouseEvent) => {
      mousePosition.x = (e.clientX / window.innerWidth) * 2 - 1;
      mousePosition.y = -(e.clientY / window.innerHeight) * 2 + 1;
    };
    window.addEventListener('mousemove', handleMouseMove);

    // Animation loop
    const clock = new THREE.Clock();
    const animate = () => {
      const elapsedTime = clock.getElapsedTime();

      // Animate particles
      particles.forEach((particle) => {
        particle.position.y += Math.sin(elapsedTime * particle.userData.speed + particle.userData.offset) * 0.01;
        particle.rotation.x += 0.01;
        particle.rotation.y += 0.01;
      });

      // Animate helix
      helixGroup.rotation.y = elapsedTime * 0.1;

      // Animate torus with mouse
      torusMesh.rotation.x = elapsedTime * 0.05 + mousePosition.y * 0.3;
      torusMesh.rotation.y = elapsedTime * 0.05 + mousePosition.x * 0.3;

      renderer.render(scene, camera);
      requestAnimationFrame(animate);
    };
    animate();

    // Handle resize
    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100vh',
        zIndex: 0,
        pointerEvents: 'none',
        opacity: 0.6,
      }}
    />
  );
}
