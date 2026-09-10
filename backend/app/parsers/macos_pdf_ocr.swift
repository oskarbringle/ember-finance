import CoreGraphics
import Foundation
import PDFKit
import Vision

guard CommandLine.arguments.count == 2 else {
    fputs("Usage: ember-pdf-ocr PDF\n", stderr)
    exit(2)
}

guard let document = PDFDocument(url: URL(fileURLWithPath: CommandLine.arguments[1])) else {
    fputs("Unable to open PDF\n", stderr)
    exit(1)
}

for pageIndex in 0..<document.pageCount {
    guard let page = document.page(at: pageIndex) else { continue }
    let bounds = page.bounds(for: .mediaBox)
    let scale: CGFloat = 2
    guard let context = CGContext(
        data: nil,
        width: Int(bounds.width * scale),
        height: Int(bounds.height * scale),
        bitsPerComponent: 8,
        bytesPerRow: 0,
        space: CGColorSpaceCreateDeviceRGB(),
        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
    ) else { continue }

    context.setFillColor(CGColor(gray: 1, alpha: 1))
    context.fill(
        CGRect(x: 0, y: 0, width: bounds.width * scale, height: bounds.height * scale)
    )
    context.scaleBy(x: scale, y: scale)
    page.draw(with: .mediaBox, to: context)
    guard let image = context.makeImage() else { continue }

    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["en-US"]
    request.usesLanguageCorrection = false
    request.minimumTextHeight = 0.006
    try VNImageRequestHandler(cgImage: image).perform([request])

    for observation in request.results ?? [] {
        guard let candidate = observation.topCandidates(1).first else { continue }
        let box = observation.boundingBox
        let text = candidate.string.replacingOccurrences(of: "\t", with: " ")
        print("\(pageIndex + 1)\t\(box.minX)\t\(box.minY)\t\(box.width)\t\(box.height)\t\(text)")
    }
}
