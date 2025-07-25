import { useEffect, useRef, useState } from 'react';
import styles from './TypingBackground.module.css';

const TypingBackground = () => {
  const canvasRef = useRef(null);
  const [dimensions, setDimensions] = useState({
    width: typeof window !== 'undefined' ? window.innerWidth : 0,
    height: typeof window !== 'undefined' ? window.innerHeight : 0,
  });
  
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    // Set initial canvas style
    canvas.style.display = 'block';
    const ctx = canvas.getContext('2d');
    
    // Set canvas size to window size
    const resizeCanvas = () => {
      const width = window.innerWidth;
      const height = window.innerHeight;
      canvas.width = width;
      canvas.height = height;
      setDimensions({ width, height });
    };
    
    // Initial resize
    resizeCanvas();
    
    // Characters to show in the matrix effect
    const characters = '01';
    const fontSize = 16;
    const columns = Math.floor(dimensions.width / fontSize);
    
    // Array of drops - one per column
    const drops = [];
    const dropSpeeds = [];
    const opacities = [];
    
    for (let i = 0; i < columns; i++) {
      drops[i] = Math.random() * -100; // Start drops at random positions above the viewport
      dropSpeeds[i] = 0.5 + Math.random() * 2; // Random speed for each column
      opacities[i] = 0.1 + Math.random() * 0.9; // Random opacity for each column
    }
    
    // Color gradient for the text - darker and more vibrant
    const colors = [
      'rgba(0, 60, 200, 0.9)',   // Darker Blue
      'rgba(0, 140, 255, 0.9)',  // Medium Blue
      'rgba(0, 180, 255, 0.9)',  // Brighter Blue
    ];
    
    // Drawing the characters
    const draw = () => {
      // Dark background with subtle fade
      ctx.fillStyle = 'rgba(0, 10, 30, 0.2)';
      ctx.fillRect(0, 0, dimensions.width, dimensions.height);
      
      // Set the font
      ctx.font = `${fontSize}px 'Fira Code', monospace`;
      
      // Loop over drops
      for (let i = 0; i < drops.length; i++) {
        // Random character to print
        const text = characters.charAt(Math.floor(Math.random() * characters.length));
        
        // Create gradient for the text
        const gradient = ctx.createLinearGradient(0, 0, 0, dimensions.height);
        gradient.addColorStop(0, colors[Math.floor(Math.random() * colors.length)]);
        gradient.addColorStop(1, colors[Math.floor(Math.random() * colors.length)]);
        
        // Set the style for the characters with gradient
        ctx.fillStyle = gradient;
        
        // Stronger glow effect
        ctx.shadowBlur = 8;
        ctx.shadowColor = 'rgba(0, 100, 255, 0.9)';
        
        // Draw the character
        ctx.fillText(text, i * fontSize, drops[i]);
        
        // Reset drop to top when it reaches bottom
        if (drops[i] > dimensions.height && Math.random() > 0.97) {
          drops[i] = 0;
          opacities[i] = 0.1 + Math.random() * 0.9;
        }
        
        // Move the drop down with variable speed
        drops[i] += dropSpeeds[i];
        
        // Randomly change speed occasionally
        if (Math.random() > 0.99) {
          dropSpeeds[i] = 0.5 + Math.random() * 2;
        }
      }
      
      // Remove shadow after drawing
      ctx.shadowBlur = 0;
    };
    
    // Handle window resize with debounce
    let resizeTimeout;
    const handleResize = () => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        resizeCanvas();
      }, 100);
    };
    
    window.addEventListener('resize', handleResize);
    
    // Animation loop with requestAnimationFrame for smoother animation
    let animationFrameId;
    const animate = () => {
      draw();
      animationFrameId = requestAnimationFrame(animate);
    };
    
    // Start the animation
    animate();
    
    // Cleanup
    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
      clearTimeout(resizeTimeout);
    };
  }, []);
  
  return (
    <div className={styles.canvasContainer}>
      <canvas 
        ref={canvasRef} 
        className={styles.typingBackground}
        width={dimensions.width}
        height={dimensions.height}
      />
      <div className={styles.overlay}></div>
    </div>
  );
};

export default TypingBackground;
