const TARGET_SAMPLE_RATE = 16_000

function downsample(input: Float32Array, inputRate: number): Float32Array {
  if (inputRate === TARGET_SAMPLE_RATE) return input.slice()
  const ratio = inputRate / TARGET_SAMPLE_RATE
  const length = Math.max(1, Math.round(input.length / ratio))
  const output = new Float32Array(length)
  for (let i = 0; i < length; i += 1) {
    const start = Math.floor(i * ratio)
    const end = Math.min(input.length, Math.floor((i + 1) * ratio))
    let sum = 0
    for (let j = start; j < end; j += 1) sum += input[j]
    output[i] = sum / Math.max(1, end - start)
  }
  return output
}

function toPcm16(input: Float32Array): ArrayBuffer {
  const buffer = new ArrayBuffer(input.length * 2)
  const view = new DataView(buffer)
  input.forEach((sample, index) => {
    const clamped = Math.max(-1, Math.min(1, sample))
    view.setInt16(index * 2, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true)
  })
  return buffer
}

export class PcmStreamer {
  private context: AudioContext | null = null
  private source: MediaStreamAudioSourceNode | null = null
  private processor: ScriptProcessorNode | null = null
  private gain: GainNode | null = null

  async start(stream: MediaStream, onChunk: (chunk: ArrayBuffer) => void): Promise<void> {
    const context = new AudioContext()
    await context.resume()
    const source = context.createMediaStreamSource(stream)
    const processor = context.createScriptProcessor(4096, 1, 1)
    const gain = context.createGain()
    gain.gain.value = 0
    processor.onaudioprocess = (event) => {
      const input = event.inputBuffer.getChannelData(0)
      onChunk(toPcm16(downsample(input, context.sampleRate)))
    }
    source.connect(processor)
    processor.connect(gain)
    gain.connect(context.destination)
    this.context = context
    this.source = source
    this.processor = processor
    this.gain = gain
  }

  async pause(): Promise<void> {
    await this.context?.suspend()
  }

  async resume(): Promise<void> {
    await this.context?.resume()
  }

  async stop(): Promise<void> {
    if (this.processor) this.processor.onaudioprocess = null
    this.source?.disconnect()
    this.processor?.disconnect()
    this.gain?.disconnect()
    await this.context?.close()
    this.context = null
    this.source = null
    this.processor = null
    this.gain = null
  }
}

export function recordingMimeType(): string | null {
  const candidates = ['video/webm;codecs=vp8,opus', 'video/webm;codecs=vp9,opus', 'video/webm']
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) ?? null
}
