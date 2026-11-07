using System.Buffers.Binary;

// Inspect the raster container and dimensions rather than trusting a filename or a client MIME type.
// The service does not decode or re-encode images; all downloads are served with a fixed raster MIME type.
static class ImageFormats
{
    private static ReadOnlySpan<byte> PngSignature => [137, 80, 78, 71, 13, 10, 26, 10];
    private static readonly uint[] CrcTable = Enumerable.Range(0, 256).Select(index =>
    {
        var crc = (uint)index;
        for (var i = 0; i < 8; i++)
            crc = (crc >> 1) ^ ((crc & 1) == 0 ? 0 : 0xedb88320u);
        return crc;
    }).ToArray();

    public static string? Detect(ReadOnlySpan<byte> data)
    {
        if (data.StartsWith(PngSignature) && Png(data)) return "image/png";
        if (data is [0xff, 0xd8, ..] && Jpeg(data)) return "image/jpeg";
        if ((data.StartsWith("GIF87a"u8) || data.StartsWith("GIF89a"u8)) && Gif(data)) return "image/gif";
        if (data.StartsWith("RIFF"u8) && WebP(data)) return "image/webp";
        return null;
    }

    private static bool ValidSize(uint width, uint height) => width is > 0 and <= 16384
        && height is > 0 and <= 16384 && (ulong)width * height <= 80000000;

    private static bool Png(ReadOnlySpan<byte> data)
    {
        var i = 8;
        var hasData = false;
        while (i <= data.Length - 12)
        {
            var length = BinaryPrimitives.ReadUInt32BigEndian(data[i..]);
            if (length > data.Length - i - 12) return false;
            var type = data.Slice(i + 4, 4);
            var payload = data.Slice(i + 8, (int)length);
            var next = i + (int)length + 12;
            var crc = uint.MaxValue;
            foreach (var octet in data[(i + 4)..(next - 4)])
                crc = (crc >> 8) ^ CrcTable[(crc ^ octet) & 255];
            if (~crc != BinaryPrimitives.ReadUInt32BigEndian(data[(next - 4)..])) return false;
            if (i == 8 && (!type.SequenceEqual("IHDR"u8) || length != 13
                || !ValidSize(BinaryPrimitives.ReadUInt32BigEndian(payload), BinaryPrimitives.ReadUInt32BigEndian(payload[4..]))))
                return false;
            if (type.SequenceEqual("IDAT"u8) && length > 0) hasData = true;
            if (type.SequenceEqual("IEND"u8)) return length == 0 && hasData && next == data.Length;
            i = next;
        }
        return false;
    }

    private static bool Jpeg(ReadOnlySpan<byte> data)
    {
        var hasFrame = false;
        var hasScan = false;
        var inScan = false;
        var i = 2;
        while (i < data.Length)
        {
            if (inScan)
            {
                var distance = data[i..].IndexOf((byte)0xff);
                if (distance < 0) return false;
                i += distance;
            }
            if (data[i++] != 0xff) return false;
            while (i < data.Length && data[i] == 0xff) i++;
            if (i == data.Length) return false;
            var marker = data[i++];
            if (inScan && (marker == 0 || marker is >= 0xd0 and <= 0xd7)) continue;
            if (marker == 0xd9) return hasFrame && hasScan && i == data.Length;
            inScan = false;
            if (marker == 0x01) continue;
            if (marker == 0 || marker is >= 0xd0 and <= 0xd8 || i > data.Length - 2) return false;
            var length = BinaryPrimitives.ReadUInt16BigEndian(data[i..]);
            if (length < 2 || length > data.Length - i) return false;
            if (marker is >= 0xc0 and <= 0xcf and not (0xc4 or 0xc8 or 0xcc))
            {
                if (length < 8 || !ValidSize(BinaryPrimitives.ReadUInt16BigEndian(data[(i + 5)..]),
                    BinaryPrimitives.ReadUInt16BigEndian(data[(i + 3)..]))) return false;
                hasFrame = true;
            }
            if (marker == 0xda)
            {
                if (length < 6 || !hasFrame) return false;
                inScan = hasScan = true;
            }
            i += length;
        }
        return false;
    }

    private static bool Gif(ReadOnlySpan<byte> data)
    {
        if (data.Length < 13 || !ValidSize(BinaryPrimitives.ReadUInt16LittleEndian(data[6..]),
            BinaryPrimitives.ReadUInt16LittleEndian(data[8..]))) return false;
        var i = 13 + GifColorTableSize(data[10]);
        var frames = 0;
        while (i < data.Length)
        {
            switch (data[i++])
            {
                case 0x3b: return frames > 0 && i == data.Length;
                case 0x21:
                    if (i == data.Length) return false;
                    i++; // Extension label.
                    break;
                case 0x2c:
                    if (i > data.Length - 9 || ++frames > 400 || !ValidSize(BinaryPrimitives.ReadUInt16LittleEndian(data[(i + 4)..]),
                        BinaryPrimitives.ReadUInt16LittleEndian(data[(i + 6)..]))) return false;
                    i += 9 + GifColorTableSize(data[i + 8]);
                    if (i >= data.Length || data[i++] is < 2 or > 8) return false;
                    break;
                default: return false;
            }
            while (i < data.Length && data[i] != 0) i += 1 + data[i];
            if (i >= data.Length) return false;
            i++;
        }
        return false;
    }

    private static int GifColorTableSize(byte flags) => (flags & 128) != 0 ? 3 << ((flags & 7) + 1) : 0;

    private static bool WebP(ReadOnlySpan<byte> data)
    {
        if (data.Length < 20 || !data[8..].StartsWith("WEBP"u8)
            || BinaryPrimitives.ReadUInt32LittleEndian(data[4..]) != data.Length - 8) return false;
        return WebPChunks(data[12..], allowAnimation: true);
    }

    private static bool WebPChunks(ReadOnlySpan<byte> data, bool allowAnimation)
    {
        var hasImage = false;
        var frames = 0;
        while (data.Length >= 8)
        {
            var chunk = data[..4];
            var length = BinaryPrimitives.ReadUInt32LittleEndian(data[4..]);
            if (length + (ulong)(length & 1) > (ulong)(data.Length - 8)) return false;
            var payload = data.Slice(8, (int)length);
            if (chunk.SequenceEqual("VP8 "u8))
            {
                if (length < 10 || (payload[0] & 1) != 0 || !payload[3..].StartsWith(new byte[] { 0x9d, 0x01, 0x2a })
                    || !ValidSize((uint)(BinaryPrimitives.ReadUInt16LittleEndian(payload[6..]) & 0x3fff),
                        (uint)(BinaryPrimitives.ReadUInt16LittleEndian(payload[8..]) & 0x3fff))) return false;
                hasImage = true;
            }
            if (chunk.SequenceEqual("VP8L"u8))
            {
                if (length < 5 || payload[0] != 0x2f) return false;
                var bits = BinaryPrimitives.ReadUInt32LittleEndian(payload[1..]);
                if (bits >> 29 != 0 || !ValidSize(1 + (bits & 0x3fff), 1 + ((bits >> 14) & 0x3fff))) return false;
                hasImage = true;
            }
            if (chunk.SequenceEqual("VP8X"u8) && (length != 10 || !ValidSize(1 + UInt24(payload[4..]), 1 + UInt24(payload[7..]))))
                return false;
            if (chunk.SequenceEqual("ANMF"u8))
            {
                if (!allowAnimation || length < 24 || ++frames > 400 || !ValidSize(1 + UInt24(payload[6..]), 1 + UInt24(payload[9..]))
                    || !WebPChunks(payload[16..], allowAnimation: false)) return false;
                hasImage = true;
            }
            data = data[(8 + (int)length + (int)(length & 1))..];
        }
        return hasImage && data.Length == 0;
    }

    private static uint UInt24(ReadOnlySpan<byte> bytes) => (uint)(bytes[0] | bytes[1] << 8 | bytes[2] << 16);
}
