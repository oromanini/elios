import React from 'react';
import eliteLogo from '../assets/elite.png';

const Logo = ({ size = 'md', showText = true }) => {
  const sizes = {
    sm: { image: 'h-8 w-auto', text: 'text-lg', subtitle: false },
    md: { image: 'h-12 w-auto', text: 'text-2xl', subtitle: true },
    lg: { image: 'h-16 w-auto', text: 'text-4xl', subtitle: true },
    xl: { image: 'h-20 w-auto', text: 'text-6xl', subtitle: true }
  };

  const { image, text, subtitle } = sizes[size] || sizes.md;

  return (
    <div className="flex items-center gap-3" data-testid="logo">
      <img
        src={eliteLogo}
        alt="ELIOS Performance Elite"
        className={`${image} object-contain`}
      />
      {showText && (
        <div className="flex flex-col">
          <span className={`font-bold ${text} tracking-tight text-white uppercase`} style={{ fontFamily: 'Rajdhani, sans-serif' }}>
            ELIOS
          </span>
          {subtitle && (
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
