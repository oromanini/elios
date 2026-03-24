import React from 'react';
import { Shield, Swords } from 'lucide-react';

const Logo = ({ size = 'md', showText = true }) => {
  const sizes = {
    sm: { icon: 20, text: 'text-lg' },
    md: { icon: 32, text: 'text-2xl' },
    lg: { icon: 48, text: 'text-4xl' },
    xl: { icon: 64, text: 'text-6xl' }
  };

  const { icon, text } = sizes[size] || sizes.md;

  return (
    <div className="flex items-center gap-3" data-testid="logo">
      <div className="relative logo-shield">
        <Shield 
          size={icon} 
          className="text-white fill-white/10" 
          strokeWidth={1.5}
        />
        <Swords 
          size={icon * 0.5} 
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-white"
          strokeWidth={1.5}
        />
      </div>
      {showText && (
        <div className="flex flex-col">
          <span className={`font-bold ${text} tracking-tight text-white uppercase`} style={{ fontFamily: 'Rajdhani, sans-serif' }}>
            ELIOS
          </span>
          {size !== 'sm' && (
            <span className="text-xs text-neutral-500 tracking-widest uppercase">
              Performance Elite
            </span>
          )}
        </div>
      )}
    </div>
  );
};

export default Logo;
