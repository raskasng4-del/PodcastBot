import "./index.css";
import { Composition, CalculateMetadataFunction } from "remotion";
import { QuizComposition, QuizProps } from "./QuizComposition";
import { StoryComposition, StoryProps } from "./StoryComposition";
import {
  ConjugationComposition,
  ConjugationProps,
} from "./ConjugationComposition";
import { getAudioDurationFromFile } from "./get-audio-duration";

const FPS = 30;

const calculateQuizMetadata: CalculateMetadataFunction<QuizProps> = async ({
  props,
}) => {
  const [qDur, aDur] = await Promise.all(
    [props.questionAudio, props.answerAudio].map((f) =>
      getAudioDurationFromFile(f).catch(() => 2.5),
    ),
  );
  const pauseDur = props.pauseDuration ?? 3;
  const totalDuration = qDur + pauseDur + aDur;
  return {
    durationInFrames: Math.ceil(totalDuration * FPS),
    props,
  };
};

const calculateStoryMetadata: CalculateMetadataFunction<StoryProps> = async ({
  props,
}) => {
  const audioDuration = await getAudioDurationFromFile(props.audioSrc).catch(
    () => props.lines.length * 2,
  );
  return {
    durationInFrames: Math.ceil(audioDuration * FPS),
    props,
  };
};

const calculateConjugationMetadata: CalculateMetadataFunction<
  ConjugationProps
> = async ({ props }) => {
  const durs = await Promise.all(
    props.timeline.map((t) =>
      getAudioDurationFromFile(t.audioSrc).catch(() => 1.5),
    ),
  );
  const timeline = props.timeline.map((t, i) => ({
    ...t,
    durationInFrames: Math.ceil(durs[i] * FPS),
  }));
  let startFrame = 0;
  for (const entry of timeline) {
    entry.startFrame = startFrame;
    startFrame += entry.durationInFrames;
  }
  return {
    durationInFrames: startFrame,
    props: { ...props, timeline, totalDuration: startFrame },
  };
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Quiz"
        component={QuizComposition}
        durationInFrames={255}
        fps={FPS}
        width={1080}
        height={1080}
        defaultProps={{
          imageUrl: "",
          objectName: "trompette",
          objectArticle: "une",
          questionAudio: "audio/q_trompette.mp3",
          answerAudio: "audio/a_trompette.mp3",
          questionText: "Qu'est-ce que c'est ?",
          pauseText: "Réfléchissez",
          answerPrefix: "C'est",
        }}
        calculateMetadata={calculateQuizMetadata}
      />
      <Composition
        id="Story"
        component={StoryComposition}
        durationInFrames={900}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          title: "Le Petit Chaperon Rouge",
          lines: [
            { text: "Il était une fois..." },
            { text: "Une petite fille qui habitait dans un village." },
          ],
          audioSrc: "audio/test_story.mp3",
          bgMusicSrc: "audio/bg-music.mp3",
        }}
        calculateMetadata={calculateStoryMetadata}
      />
      <Composition
        id="Conjugaison"
        component={ConjugationComposition}
        durationInFrames={300}
        fps={FPS}
        width={1080}
        height={1920}
        defaultProps={{
          verb: { infinitive: "Parler", level: "A1" },
          tense: "present",
          timeline: [
            {
              pronoun: "je",
              conjugation: "parle",
              audioSrc: "audio/conj_parler_je.mp3",
              startFrame: 0,
              durationInFrames: 30,
            },
            {
              pronoun: "tu",
              conjugation: "parles",
              audioSrc: "audio/conj_parler_tu.mp3",
              startFrame: 30,
              durationInFrames: 30,
            },
            {
              pronoun: "il/elle",
              conjugation: "parle",
              audioSrc: "audio/conj_parler_il.mp3",
              startFrame: 60,
              durationInFrames: 30,
            },
            {
              pronoun: "nous",
              conjugation: "parlons",
              audioSrc: "audio/conj_parler_nous.mp3",
              startFrame: 90,
              durationInFrames: 30,
            },
            {
              pronoun: "vous",
              conjugation: "parlez",
              audioSrc: "audio/conj_parler_vous.mp3",
              startFrame: 120,
              durationInFrames: 30,
            },
            {
              pronoun: "ils/elles",
              conjugation: "parlent",
              audioSrc: "audio/conj_parler_ils.mp3",
              startFrame: 150,
              durationInFrames: 30,
            },
          ],
          totalDuration: 300,
        }}
        calculateMetadata={calculateConjugationMetadata}
      />
    </>
  );
};
