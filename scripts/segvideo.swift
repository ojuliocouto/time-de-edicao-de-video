import Foundation
import AVFoundation
import Vision
import CoreImage

// Le um video e escreve em stdout a mascara do assunto, quadro a quadro,
// em cinza 8 bits cru, no tamanho pedido. Feito para ser canalizado no ffmpeg.
//
//   segvideo <video> <largura> <altura> [inicio_s] [duracao_s]
//
// Usa VNGenerateForegroundInstanceMaskRequest, a mesma API do "copiar assunto"
// do Preview. Ela devolve mascara na resolucao da imagem e segura muito melhor
// a borda do cabelo. Se ela falhar num quadro, cai para a segmentacao de
// pessoa, que e mais tosca mas nunca deixa o quadro sem mascara.

let a = CommandLine.arguments
guard a.count >= 4, let W = Int(a[2]), let H = Int(a[3]) else {
    FileHandle.standardError.write("uso: segvideo <video> <larg> <alt> [inicio] [duracao]\n".data(using: .utf8)!)
    exit(2)
}
let inicio = a.count > 4 ? Double(a[4]) ?? 0 : 0
let duracao = a.count > 5 ? Double(a[5]) ?? .infinity : .infinity

let asset = AVURLAsset(url: URL(fileURLWithPath: a[1]))
guard let track = asset.tracks(withMediaType: .video).first else {
    FileHandle.standardError.write("sem trilha de video\n".data(using: .utf8)!); exit(1)
}
let reader = try! AVAssetReader(asset: asset)
if inicio > 0 || duracao != .infinity {
    let dur = duracao == .infinity ? asset.duration.seconds - inicio : duracao
    reader.timeRange = CMTimeRange(start: CMTime(seconds: inicio, preferredTimescale: 600),
                                   duration: CMTime(seconds: dur, preferredTimescale: 600))
}
let out = AVAssetReaderTrackOutput(track: track,
    outputSettings: [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA])
out.alwaysCopiesSampleData = false
reader.add(out)
reader.startReading()

let reserva = VNGeneratePersonSegmentationRequest()
reserva.qualityLevel = .accurate
reserva.outputPixelFormat = kCVPixelFormatType_OneComponent8

let ctx = CIContext(options: [.useSoftwareRenderer: false])
let cinza = CGColorSpaceCreateDeviceGray()
var buffer = [UInt8](repeating: 0, count: W * H)
let stdout = FileHandle.standardOutput
var n = 0, quedas = 0

while let sample = out.copyNextSampleBuffer() {
    guard let px = CMSampleBufferGetImageBuffer(sample) else { continue }
    let handler = VNImageRequestHandler(cvPixelBuffer: px, options: [:])
    var mascara: CIImage? = nil

    let req = VNGenerateForegroundInstanceMaskRequest()
    if (try? handler.perform([req])) != nil, let obs = req.results?.first,
       let m = try? obs.generateScaledMaskForImage(forInstances: obs.allInstances, from: handler) {
        mascara = CIImage(cvPixelBuffer: m)
    } else {
        quedas += 1
        let h2 = VNImageRequestHandler(cvPixelBuffer: px, options: [:])
        if (try? h2.perform([reserva])) != nil, let o = reserva.results?.first {
            mascara = CIImage(cvPixelBuffer: o.pixelBuffer)
        }
    }

    if let m = mascara {
        let sx = CGFloat(W) / m.extent.width, sy = CGFloat(H) / m.extent.height
        let esticada = m.transformed(by: CGAffineTransform(scaleX: sx, y: sy))
        buffer.withUnsafeMutableBytes { p in
            ctx.render(esticada, toBitmap: p.baseAddress!, rowBytes: W,
                       bounds: CGRect(x: 0, y: 0, width: W, height: H),
                       format: .L8, colorSpace: cinza)
        }
    } else {
        for i in 0..<buffer.count { buffer[i] = 0 }
    }
    stdout.write(Data(buffer))
    n += 1
}
FileHandle.standardError.write("quadros: \(n) | quedas para a API de reserva: \(quedas)\n".data(using: .utf8)!)
