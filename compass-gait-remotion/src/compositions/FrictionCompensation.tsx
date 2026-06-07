import React from 'react';
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
  spring,
} from 'remotion';

interface FrictionCompensationProps {
  showComparison?: boolean;
}

/**
 * V13.7 摩擦补偿对比动画
 * 展示有无摩擦补偿的性能差异
 */
export const FrictionCompensation: React.FC<FrictionCompensationProps> = ({
  showComparison = true,
}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();

  const progress = frame / durationInFrames;

  // 模拟行走数据：无补偿 vs 有补偿
  const withoutCompensation = {
    distance: 3.2,
    success: false,
    stepCount: 7,
    energyLoss: 25.6,
    stability: 0.45,
  };

  const withCompensation = {
    distance: 4.85,
    success: true,
    stepCount: 11,
    energyLoss: 8.2,
    stability: 0.82,
  };

  // 动画进度
  const stage1Progress = interpolate(progress, [0, 0.3], [0, 1], {
    extrapolateRight: 'clamp',
  });

  const stage2Progress = interpolate(progress, [0.3, 0.7], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const stage3Progress = interpolate(progress, [0.7, 1.0], [0, 1], {
    extrapolateLeft: 'clamp',
  });

  // 弹簧动画
  const bounceScale = spring({
    frame: frame % 30,
    fps,
    config: {
      damping: 12,
      stiffness: 100,
    },
  });

  return (
    <AbsoluteFill style={{backgroundColor: '#0F172A'}}>
      {/* 标题 */}
      <div
        style={{
          position: 'absolute',
          top: 40,
          left: 0,
          right: 0,
          textAlign: 'center',
          color: '#F1F5F9',
          fontSize: 56,
          fontWeight: 'bold',
          fontFamily: 'Arial, sans-serif',
        }}
      >
        V13.7 摩擦补偿技术
      </div>

      {/* 副标题 */}
      <div
        style={{
          position: 'absolute',
          top: 120,
          left: 0,
          right: 0,
          textAlign: 'center',
          color: '#94A3B8',
          fontSize: 32,
          fontFamily: 'Arial, sans-serif',
        }}
      >
        Friction Compensation for Stable Gait
      </div>

      {/* 对比区域 */}
      <div
        style={{
          position: 'absolute',
          top: 220,
          left: 80,
          right: 80,
          bottom: 180,
          display: 'flex',
          gap: 40,
        }}
      >
        {/* 无补偿 */}
        <ComparisonCard
          title="无摩擦补偿"
          subtitle="Baseline"
          color="#EF4444"
          metrics={withoutCompensation}
          progress={stage1Progress}
          icon="❌"
        />

        {/* VS 标识 */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 120,
            transform: `scale(${1 + bounceScale * 0.3})`,
          }}
        >
          <div
            style={{
              fontSize: 72,
              fontWeight: 'bold',
              color: '#FBBF24',
              fontFamily: 'Arial, sans-serif',
            }}
          >
            VS
          </div>
        </div>

        {/* 有补偿 */}
        <ComparisonCard
          title="有摩擦补偿"
          subtitle="V13.7"
          color="#10B981"
          metrics={withCompensation}
          progress={stage2Progress}
          icon="✓"
        />
      </div>

      {/* 关键改进说明 */}
      <div
        style={{
          position: 'absolute',
          bottom: 60,
          left: 80,
          right: 80,
          opacity: stage3Progress,
        }}
      >
        <div
          style={{
            backgroundColor: '#1E293B',
            borderRadius: 16,
            padding: 30,
            display: 'grid',
            gridTemplateColumns: '1fr 1fr 1fr',
            gap: 30,
          }}
        >
          <Feature
            icon="⚡"
            title="能量损失减少"
            value="-68%"
            color="#FBBF24"
          />
          <Feature
            icon="📈"
            title="行走距离增加"
            value="+52%"
            color="#10B981"
          />
          <Feature
            icon="🎯"
            title="稳定性提升"
            value="+82%"
            color="#3B82F6"
          />
        </div>
      </div>

      {/* 进度指示器 */}
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
        Frame: {frame}
      </div>
    </AbsoluteFill>
  );
};

// 对比卡片组件
const ComparisonCard: React.FC<{
  title: string;
  subtitle: string;
  color: string;
  metrics: any;
  progress: number;
  icon: string;
}> = ({title, subtitle, color, metrics, progress, icon}) => {
  return (
    <div
      style={{
        flex: 1,
        backgroundColor: '#1E293B',
        borderRadius: 20,
        padding: 40,
        border: `4px solid ${color}`,
        opacity: progress,
        transform: `translateY(${(1 - progress) * 50}px)`,
        transition: 'all 0.3s ease',
      }}
    >
      {/* 标题 */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 15,
          marginBottom: 30,
        }}
      >
        <div style={{fontSize: 40}}>{icon}</div>
        <div>
          <div
            style={{
              color: '#F1F5F9',
              fontSize: 32,
              fontWeight: 'bold',
              fontFamily: 'Arial, sans-serif',
            }}
          >
            {title}
          </div>
          <div
            style={{
              color: '#94A3B8',
              fontSize: 20,
              fontFamily: 'Arial, sans-serif',
            }}
          >
            {subtitle}
          </div>
        </div>
      </div>

      {/* 指标 */}
      <div style={{display: 'flex', flexDirection: 'column', gap: 25}}>
        <MetricRow
          label="行走距离"
          value={`${(metrics.distance * progress).toFixed(1)} m`}
          color={color}
        />
        <MetricRow
          label="成功步数"
          value={`${Math.round(metrics.stepCount * progress)} 步`}
          color={color}
        />
        <MetricRow
          label="能量损失"
          value={`${(metrics.energyLoss * progress).toFixed(1)} J`}
          color={color}
        />
        <MetricRow
          label="稳定性"
          value={`${(metrics.stability * progress * 100).toFixed(0)}%`}
          color={color}
        />
        <div
          style={{
            marginTop: 20,
            padding: 20,
            backgroundColor: metrics.success ? '#10B98120' : '#EF444420',
            borderRadius: 12,
            textAlign: 'center',
            color: metrics.success ? '#10B981' : '#EF4444',
            fontSize: 24,
            fontWeight: 'bold',
            fontFamily: 'Arial, sans-serif',
          }}
        >
          {metrics.success ? '行走成功 ✓' : '失败倒地 ✗'}
        </div>
      </div>
    </div>
  );
};

// 指标行组件
const MetricRow: React.FC<{
  label: string;
  value: string;
  color: string;
}> = ({label, value, color}) => {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}
    >
      <span
        style={{
          color: '#94A3B8',
          fontSize: 20,
          fontFamily: 'Arial, sans-serif',
        }}
      >
        {label}
      </span>
      <span
        style={{
          color: color,
          fontSize: 28,
          fontWeight: 'bold',
          fontFamily: 'monospace',
        }}
      >
        {value}
      </span>
    </div>
  );
};

// 特性组件
const Feature: React.FC<{
  icon: string;
  title: string;
  value: string;
  color: string;
}> = ({icon, title, value, color}) => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 15,
      }}
    >
      <div style={{fontSize: 48}}>{icon}</div>
      <div
        style={{
          color: '#F1F5F9',
          fontSize: 20,
          textAlign: 'center',
          fontFamily: 'Arial, sans-serif',
        }}
      >
        {title}
      </div>
      <div
        style={{
          color: color,
          fontSize: 36,
          fontWeight: 'bold',
          fontFamily: 'monospace',
        }}
      >
        {value}
      </div>
    </div>
  );
};
