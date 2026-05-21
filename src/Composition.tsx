import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  useVideoConfig,
  Easing,
  Sequence,
} from "remotion";

const backgroundColor = "#1a1a2e";

export const Title: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = interpolate(frame, [0, fps], [0, 1], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  const scale = interpolate(frame, [0, fps], [0.8, 1], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  return (
    <div
      style={{
        fontFamily: "Arial, sans-serif",
        fontSize: 80,
        fontWeight: 700,
        color: "#e94560",
        opacity,
        transform: `scale(${scale})`,
        textAlign: "center",
      }}
    >
      {text}
    </div>
  );
};

export const Subtitle: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = interpolate(frame, [0, fps * 1.5], [0, 1], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  const y = interpolate(frame, [0, fps * 1.5], [30, 0], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  return (
    <div
      style={{
        fontFamily: "Arial, sans-serif",
        fontSize: 32,
        fontWeight: 400,
        color: "#ffffff",
        opacity,
        transform: `translateY(${y}px)`,
        textAlign: "center",
        marginTop: 20,
      }}
    >
      {text}
    </div>
  );
};

export const Box: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const rotation = interpolate(frame, [0, 3 * fps], [0, 360], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  return (
    <div
      style={{
        width: 60,
        height: 60,
        borderRadius: 12,
        backgroundColor: "#0f3460",
        border: "2px solid #e94560",
        transform: `rotate(${rotation}deg)`,
        marginBottom: 40,
      }}
    />
  );
};

export const MyComposition: React.FC = () => {
  const { fps } = useVideoConfig();
  const frame = useCurrentFrame();

  const bgOpacity = interpolate(frame, [0, fps], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor,
        justifyContent: "center",
        alignItems: "center",
        opacity: bgOpacity,
      }}
    >
      <Sequence from={0} durationInFrames={10 * fps}>
        <AbsoluteFill
          style={{ justifyContent: "center", alignItems: "center" }}
        >
          <Box />
          <Title text="Hello World" />
          <Sequence from={fps} durationInFrames={8 * fps} layout="none">
            <Subtitle text="Made with Remotion" />
          </Sequence>
        </AbsoluteFill>
      </Sequence>
    </AbsoluteFill>
  );
};
