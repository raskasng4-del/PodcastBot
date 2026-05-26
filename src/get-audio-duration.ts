import { Input, ALL_FORMATS, UrlSource, FileSource } from "mediabunny";
import { staticFile } from "remotion";

export const getAudioDuration = async (src: string) => {
  const input = new Input({
    formats: ALL_FORMATS,
    source: new UrlSource(src, {
      getRetryDelay: () => null,
    }),
  });
  const durationInSeconds = await input.computeDuration();
  return durationInSeconds;
};

export const getAudioDurationFromFile = async (filePath: string) => {
  const input = new Input({
    formats: ALL_FORMATS,
    source: new FileSource(
      await fetch(staticFile(filePath)).then((r) => r.blob()),
    ),
  });
  return input.computeDuration();
};
