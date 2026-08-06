import CoreGraphics
import Foundation
import ImageIO
import UniformTypeIdentifiers

enum NormalizationError: Error, CustomStringConvertible {
    case message(String)

    var description: String {
        switch self {
        case let .message(text): text
        }
    }
}

func normalize() throws {
    let arguments = CommandLine.arguments
    guard arguments.count == 5 else {
        throw NormalizationError.message(
            "usage: normalize_png_canvas.swift INPUT OUTPUT TARGET_WIDTH TARGET_HEIGHT"
        )
    }

    let inputURL = URL(fileURLWithPath: arguments[1])
    let outputURL = URL(fileURLWithPath: arguments[2])
    guard
        let targetWidth = Int(arguments[3]),
        let targetHeight = Int(arguments[4]),
        targetWidth > 0,
        targetHeight > 0
    else {
        throw NormalizationError.message("target dimensions must be positive integers")
    }

    guard
        let source = CGImageSourceCreateWithURL(inputURL as CFURL, nil),
        CGImageSourceGetType(source) == UTType.png.identifier as CFString,
        let image = CGImageSourceCreateImageAtIndex(source, 0, nil)
    else {
        throw NormalizationError.message("input is not a readable PNG")
    }

    let cropWidth = min(image.width, targetWidth)
    let cropHeight = min(image.height, targetHeight)
    let cropX = (image.width - cropWidth) / 2
    let cropY = (image.height - cropHeight) / 2
    let cropRect = CGRect(x: cropX, y: cropY, width: cropWidth, height: cropHeight)
    guard let cropped = image.cropping(to: cropRect) else {
        throw NormalizationError.message("failed to crop the PNG canvas")
    }

    let colorSpace: CGColorSpace
    if let sourceColorSpace = cropped.colorSpace, sourceColorSpace.model == .rgb {
        colorSpace = sourceColorSpace
    } else if let sRGB = CGColorSpace(name: CGColorSpace.sRGB) {
        colorSpace = sRGB
    } else {
        throw NormalizationError.message("failed to create an RGB color space")
    }

    let bitmapInfo = CGBitmapInfo.byteOrder32Big.rawValue
        | CGImageAlphaInfo.premultipliedLast.rawValue
    guard let context = CGContext(
        data: nil,
        width: targetWidth,
        height: targetHeight,
        bitsPerComponent: 8,
        bytesPerRow: 0,
        space: colorSpace,
        bitmapInfo: bitmapInfo
    ) else {
        throw NormalizationError.message("failed to create a transparent PNG canvas")
    }

    context.clear(CGRect(x: 0, y: 0, width: targetWidth, height: targetHeight))
    context.interpolationQuality = .none
    let drawX = (targetWidth - cropped.width) / 2
    let drawY = (targetHeight - cropped.height) / 2
    context.draw(
        cropped,
        in: CGRect(x: drawX, y: drawY, width: cropped.width, height: cropped.height)
    )

    guard let outputImage = context.makeImage() else {
        throw NormalizationError.message("failed to render the normalized PNG")
    }
    guard let destination = CGImageDestinationCreateWithURL(
        outputURL as CFURL,
        UTType.png.identifier as CFString,
        1,
        nil
    ) else {
        throw NormalizationError.message("failed to open the output PNG")
    }

    CGImageDestinationAddImage(destination, outputImage, nil)
    guard CGImageDestinationFinalize(destination) else {
        throw NormalizationError.message("failed to write the output PNG")
    }
}

do {
    try normalize()
} catch {
    FileHandle.standardError.write(Data("error: \(error)\n".utf8))
    exit(1)
}
