import React from 'react';
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

interface RollingFootAnimationProps {
  dataFile: string;
}

export const RollingFootAnimation: React.FC<RollingFootAnimationProps> = () => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();

  // Simulate a complete gait cycle over the duration
  const cycleProgress = (frame % 150) / 150; // One cycle every 5 seconds at 30fps

  // Define the three contact phases
  const phases = [
    {name: 'heel', label: '脚跟接触', range: [0, 0.3], color: '#EF4444'},
    {name: 'sole', label: '足底滚动', range: [0.25, 0.7], color: '#F59E0B'},
    {name: 'toe', label: '脚趾离地', range: [0.65, 1.0], color: '#10B981'},
  ];

  // Determine active phase
  let activePhase = 'heel';
  let phaseOpacity = {heel: 0.3, sole: 0.3, toe: 0.3};

  for (const phase of phases) {
    if (cycleProgress >= phase.range[0] && cycleProgress <= phase.range[1]) {
      activePhase = phase.name;
      const localProgress =
        (cycleProgress - phase.range[0]) / (phase.range[1] - phase.range[0]);
      phaseOpacity[phase.name as keyof typeof phaseOpacity] = 0.3 + 0.7 * Math.sin(localProgress * Math.PI);
    }
  }

  // Foot rotation angle (roll from heel to toe)
  const footAngle = interpolate(cycleProgress, [0, 0.3, 0.7, 1.0], [-15, 0, 15, 20], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Ground contact point movement
  const contactX = interpolate(cycleProgress, [0, 0.3, 0.7, 1.0], [0, 0, 50, 100]);

  return (
    <AbsoluteFill style={{backgroundColor: '#0F172A'}}>
      {/* Title */}
      <div
        style={{
          position: 'absolute',
          top: 60,
          left: 0,
          right: 0,
          textAlign: 'center',
          color: '#F1F5F9',
          fontSize: 64,
          fontWeight: 'bold',
          fontFamily: 'Arial, sans-serif',
        }}
      >
        V10 足踝滚动仿生步态
      </div>

      {/* Subtitle */}
      <div
        style={{
          position: 'absolute',
          top: 140,
          left: 0,
          right: 0,
          textAlign: 'center',
          color: '#94A3B8',
          fontSize: 32,
          fontFamily: 'Arial, sans-serif',
        }}
      >
        脚跟接触 → 足底滚动 → 脚趾离地
      </div>

      {/* Main visualization area */}
      <div
        style={{
          position: 'absolute',
          top: 300,
          left: 0,
          right: 0,
          height: 400,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
        }}
      >
        {/* Ground line */}
        <div
          style={{
            position: 'absolute',
            bottom: 100,
            left: 200,
            right: 200,
            height: 4,
            backgroundColor: '#475569',
          }}
        />

        {/* Foot representation */}
        <div
          style={{
            position: 'relative',
            width: 300,
            height: 100,
            transform: `rotate(${footAngle}deg) translateX(${contactX}px)`,
            transformOrigin: 'center center',
          }}
        >
          {/* Heel */}
          <div
            style={{
              position: 'absolute',
              left: 0,
              bottom: 0,
              width: 80,
              height: 60,
              borderRadius: '50% 0 0 50%',
              backgroundColor: '#EF4444',
              opacity: phaseOpacity.heel,
              border: activePhase === 'heel' ? '4px solid #FBBF24' : '2px solid #1E293B',
              boxShadow:
                activePhase === 'heel'
                  ? '0 0 30px rgba(239, 68, 68, 0.8)'
                  : 'none',
            }}
          >
            {activePhase === 'heel' && (
              <div
                style={{
                  position: 'absolute',
                  bottom: -40,
                  left: 20,
                  color: '#FBBF24',
                  fontSize: 20,
                  fontWeight: 'bold',
                  whiteSpace: 'nowrap',
                  fontFamily: 'Arial, sans-serif',
                }}
              >
                脚跟
              </div>
            )}
          </div>

          {/* Sole */}
          <div
            style={{
              position: 'absolute',
              left: 70,
              bottom: 0,
              width: 140,
              height: 50,
              backgroundColor: '#F59E0B',
              opacity: phaseOpacity.sole,
              border: activePhase === 'sole' ? '4px solid #FBBF24' : '2px solid #1E293B',
              boxShadow:
                activePhase === 'sole'
                  ? '0 0 30px rgba(245, 158, 11, 0.8)'
                  : 'none',
            }}
          >
            {activePhase === 'sole' && (
              <div
                style={{
                  position: 'absolute',
                  bottom: -40,
                  left: 40,
                  color: '#FBBF24',
                  fontSize: 20,
                  fontWeight: 'bold',
                  whiteSpace: 'nowrap',
                  fontFamily: 'Arial, sans-serif',
                }}
              >
                足底
              </div>
            )}
          </div>

          {/* Toe */}
          <div
            style={{
              position: 'absolute',
              right: 0,
              bottom: 0,
              width: 90,
              height: 45,
              borderRadius: '0 50% 50% 0',
              backgroundColor: '#10B981',
              opacity: phaseOpacity.toe,
              border: activePhase === 'toe' ? '4px solid #FBBF24' : '2px solid #1E293B',
              boxShadow:
                activePhase === 'toe'
                  ? '0 0 30px rgba(16, 185, 129, 0.8)'
                  : 'none',
            }}
          >
            {activePhase === 'toe' && (
              <div
                style={{
                  position: 'absolute',
                  bottom: -40,
                  right: 20,
                  color: '#FBBF24',
                  fontSize: 20,
                  fontWeight: 'bold',
                  whiteSpace: 'nowrap',
                  fontFamily: 'Arial, sans-serif',
                }}
              >
                脚趾
              </div>
            )}
          </div>

          {/* Ankle joint */}
          <div
            style={{
              position: 'absolute',
              left: 120,
              top: -20,
              width: 20,
              height: 20,
              borderRadius: '50%',
              backgroundColor: '#60A5FA',
              border: '3px solid #F1F5F9',
            }}
          />
        </div>
      </div>

      {/* Phase timeline */}
      <div
        style={{
          position: 'absolute',
          bottom: 200,
          left: 200,
          right: 200,
          height: 80,
        }}
      >
        <div
          style={{
            position: 'relative',
            width: '100%',
            height: 40,
            backgroundColor: '#1E293B',
            borderRadius: 20,
            overflow: 'hidden',
          }}
        >
          {/* Progress bar */}
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              width: `${cycleProgress * 100}%`,
              height: '100%',
              backgroundColor: '#FBBF24',
              transition: 'width 0.1s linear',
            }}
          />

          {/* Phase markers */}
          {phases.map((phase, idx) => (
            <div
              key={idx}
              style={{
                position: 'absolute',
                left: `${phase.range[0] * 100}%`,
                width: `${(phase.range[1] - phase.range[0]) * 100}%`,
                top: 50,
                color: '#F1F5F9',
                fontSize: 18,
                textAlign: 'center',
                fontFamily: 'Arial, sans-serif',
              }}
            >
              {phase.label}
            </div>
          ))}
        </div>
      </div>

      {/* Key features */}
      <div
        style={{
          position: 'absolute',
          bottom: 60,
          left: 200,
          color: '#94A3B8',
          fontSize: 20,
          fontFamily: 'Arial, sans-serif',
          lineHeight: 1.8,
        }}
      >
        <div>✓ 被动踝关节弹簧阻尼</div>
        <div>✓ 脚跟-足底-脚趾连续滚动</div>
        <div>✓ 准被动仿生机械转译</div>
      </div>

      {/* Cycle progress */}
      <div
        style={{
          position: 'absolute',
          top: 20,
          right: 40,
          color: '#94A3B8',
          fontSize: 20,
          fontFamily: 'monospace',
        }}
      >
        Cycle: {Math.round(cycleProgress * 100)}%
      </div>
    </AbsoluteFill>
  );
};
