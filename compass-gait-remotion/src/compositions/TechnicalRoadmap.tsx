import React from 'react';
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
  spring,
} from 'remotion';

interface TechnicalRoadmapProps {
  startVersion?: number;
  endVersion?: number;
}

/**
 * 技术路线图动画
 * 展示从V01到V25的完整技术演进
 */
export const TechnicalRoadmap: React.FC<TechnicalRoadmapProps> = ({
  startVersion = 1,
  endVersion = 25,
}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();

  const progress = frame / durationInFrames;

  // 版本里程碑
  const milestones = [
    {
      version: 'V01-V05',
      title: '基础探索',
      subtitle: 'Foundation',
      color: '#94A3B8',
      items: ['Compass Gait', 'Rimless Wheel', 'Limit Cycle', 'Hybrid Dynamics'],
      phase: 0,
    },
    {
      version: 'V06-V09',
      title: '准被动控制',
      subtitle: 'Quasi-Passive',
      color: '#3B82F6',
      items: ['能量整形', 'PD控制', '稳定步态', '仿生设计'],
      phase: 1,
    },
    {
      version: 'V10-V13',
      title: '滚动足与FSM',
      subtitle: 'Rolling Foot & FSM',
      color: '#10B981',
      items: ['足踝滚动', '事件驱动', '摩擦补偿', 'Floquet分析'],
      phase: 2,
    },
    {
      version: 'V14-V17',
      title: '执行器建模',
      subtitle: 'Actuator Modeling',
      color: '#F59E0B',
      items: ['被动臂', 'SEA设计', '电机动力学', '状态估计'],
      phase: 3,
    },
    {
      version: 'V18-V21',
      title: '3D拓展',
      subtitle: '3D Extension',
      color: '#8B5CF6',
      items: ['侧向稳定', '髋外展', '步宽控制', '扰动鲁棒'],
      phase: 4,
    },
    {
      version: 'V22-V25',
      title: '硬件实现',
      subtitle: 'Hardware',
      color: '#EC4899',
      items: ['机械设计', '系统辨识', 'Sim-to-Real', '实物测试'],
      phase: 5,
    },
  ];

  // 当前激活的里程碑
  const currentPhase = Math.floor(progress * milestones.length);

  // 弹簧动画
  const bounceScale = spring({
    frame: frame % 20,
    fps,
    config: {
      damping: 10,
      stiffness: 150,
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
          fontSize: 64,
          fontWeight: 'bold',
          fontFamily: 'Arial, sans-serif',
        }}
      >
        技术路线图
      </div>

      {/* 副标题 */}
      <div
        style={{
          position: 'absolute',
          top: 130,
          left: 0,
          right: 0,
          textAlign: 'center',
          color: '#94A3B8',
          fontSize: 32,
          fontFamily: 'Arial, sans-serif',
        }}
      >
        V01 → V25 技术演进历程
      </div>

      {/* 时间轴 */}
      <div
        style={{
          position: 'absolute',
          top: 240,
          left: 100,
          right: 100,
          height: 600,
          display: 'flex',
          flexDirection: 'column',
          gap: 40,
        }}
      >
        {milestones.map((milestone, idx) => {
          const isActive = idx <= currentPhase;
          const isCurrent = idx === currentPhase;
          const itemProgress = isActive
            ? idx < currentPhase
              ? 1
              : (progress * milestones.length) % 1
            : 0;

          return (
            <div
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 30,
                opacity: isActive ? 1 : 0.3,
                transform: `translateX(${isActive ? 0 : -50}px)`,
                transition: 'all 0.5s ease',
              }}
            >
              {/* 节点 */}
              <div
                style={{
                  width: isCurrent ? 80 : 60,
                  height: isCurrent ? 80 : 60,
                  borderRadius: '50%',
                  backgroundColor: milestone.color,
                  border: `${isCurrent ? 5 : 3}px solid ${
                    isCurrent ? '#FBBF24' : '#475569'
                  }`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: isCurrent ? 24 : 20,
                  fontWeight: 'bold',
                  color: '#F1F5F9',
                  fontFamily: 'monospace',
                  boxShadow: isCurrent
                    ? `0 0 40px ${milestone.color}80`
                    : 'none',
                  transform: isCurrent ? `scale(${1 + bounceScale * 0.1})` : 'scale(1)',
                  flexShrink: 0,
                }}
              >
                {milestone.version.split('-')[0]}
              </div>

              {/* 内容卡片 */}
              <div
                style={{
                  flex: 1,
                  backgroundColor: '#1E293B',
                  borderRadius: 16,
                  padding: 25,
                  border: `3px solid ${
                    isCurrent ? milestone.color : '#334155'
                  }`,
                  opacity: itemProgress,
                  transform: `scale(${0.9 + itemProgress * 0.1})`,
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: 15,
                  }}
                >
                  <div>
                    <div
                      style={{
                        color: milestone.color,
                        fontSize: 28,
                        fontWeight: 'bold',
                        fontFamily: 'Arial, sans-serif',
                      }}
                    >
                      {milestone.title}
                    </div>
                    <div
                      style={{
                        color: '#94A3B8',
                        fontSize: 18,
                        fontFamily: 'Arial, sans-serif',
                      }}
                    >
                      {milestone.subtitle}
                    </div>
                  </div>
                  <div
                    style={{
                      color: '#64748B',
                      fontSize: 20,
                      fontWeight: 'bold',
                      fontFamily: 'monospace',
                    }}
                  >
                    {milestone.version}
                  </div>
                </div>

                {/* 关键特性 */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: 10,
                  }}
                >
                  {milestone.items.map((item, itemIdx) => (
                    <div
                      key={itemIdx}
                      style={{
                        color: '#CBD5E1',
                        fontSize: 16,
                        fontFamily: 'Arial, sans-serif',
                        padding: '8px 12px',
                        backgroundColor: '#0F172A',
                        borderRadius: 8,
                      }}
                    >
                      • {item}
                    </div>
                  ))}
                </div>
              </div>

              {/* 连接线 */}
              {idx < milestones.length - 1 && (
                <div
                  style={{
                    position: 'absolute',
                    left: 130,
                    top: idx * 140 + 120,
                    width: 4,
                    height: 40,
                    backgroundColor: isActive ? milestone.color : '#334155',
                    transition: 'all 0.3s ease',
                  }}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* 底部统计 */}
      <div
        style={{
          position: 'absolute',
          bottom: 40,
          left: 100,
          right: 100,
          display: 'flex',
          justifyContent: 'space-around',
          backgroundColor: '#1E293B',
          borderRadius: 16,
          padding: 30,
          border: '3px solid #475569',
        }}
      >
        <StatBox label="总版本数" value="25" color="#3B82F6" />
        <StatBox label="技术阶段" value="6" color="#10B981" />
        <StatBox label="研发周期" value="24个月" color="#F59E0B" />
        <StatBox label="当前进度" value={`${Math.round(progress * 100)}%`} color="#8B5CF6" />
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
        Phase: {currentPhase + 1}/{milestones.length}
      </div>
    </AbsoluteFill>
  );
};

// 统计框组件
const StatBox: React.FC<{
  label: string;
  value: string;
  color: string;
}> = ({label, value, color}) => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 10,
      }}
    >
      <div
        style={{
          color: '#94A3B8',
          fontSize: 20,
          fontFamily: 'Arial, sans-serif',
        }}
      >
        {label}
      </div>
      <div
        style={{
          color: color,
          fontSize: 42,
          fontWeight: 'bold',
          fontFamily: 'monospace',
        }}
      >
        {value}
      </div>
    </div>
  );
};
