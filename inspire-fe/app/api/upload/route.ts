import { NextResponse } from 'next/server';
import { writeFile, mkdir } from 'fs/promises';
import { join, parse } from 'path';
import { existsSync } from 'fs';

function toAsciiSlug(filename: string) {
  const parsed = parse(filename);
  const asciiBaseName = parsed.name
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'D')
    .replace(/[^a-zA-Z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .toLowerCase();

  const safeExtension = parsed.ext
    .replace(/[^a-zA-Z0-9.]/g, '')
    .toLowerCase();

  return `${asciiBaseName || 'image'}${safeExtension}`;
}

// POST /api/upload - Upload image file
export async function POST(request: Request) {
  try {
    const formData = await request.formData();
    const file = formData.get('file') as File;

    if (!file) {
      return NextResponse.json(
        { error: 'No file provided' },
        { status: 400 }
      );
    }

    // Validate file type
    if (!file.type.startsWith('image/')) {
      return NextResponse.json(
        { error: 'File must be an image' },
        { status: 400 }
      );
    }

    // Validate file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      return NextResponse.json(
        { error: 'File size must be less than 5MB' },
        { status: 400 }
      );
    }

    // Read file buffer
    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);

    // Generate unique filename
    const timestamp = Date.now();
    const filename = `${timestamp}-${toAsciiSlug(file.name)}`;

    // Ensure public/images directory exists
    const publicDir = join(process.cwd(), 'public', 'images');
    if (!existsSync(publicDir)) {
      await mkdir(publicDir, { recursive: true });
    }

    // Save file
    const filepath = join(publicDir, filename);
    await writeFile(filepath, buffer);

    // Return URL path
    const imageUrl = `/images/${filename}`;

    return NextResponse.json({ url: imageUrl }, { status: 200 });
  } catch (error) {
    console.error('Error uploading file:', error);
    return NextResponse.json(
      { error: 'Failed to upload file' },
      { status: 500 }
    );
  }
}

