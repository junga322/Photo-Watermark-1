import os
import argparse
from PIL import Image, ImageDraw, ImageFont
from PIL.ExifTags import TAGS
import datetime

def get_exif_datetime(image_path):
    """
    从图片EXIF信息中获取拍摄时间
    """
    try:
        image = Image.open(image_path)
        exif_data = image._getexif()
        
        if exif_data is not None:
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                if tag in ("DateTime", "DateTimeOriginal", "DateTimeDigitized"):
                    # 解析时间字符串，格式通常是 "YYYY:MM:DD HH:MM:SS"
                    dt = datetime.datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                    return dt.strftime("%Y-%m-%d")
        return None
    except Exception as e:
        print(f"读取 {image_path} 的EXIF信息时出错: {e}")
        return None

def add_watermark_to_image(image_path, watermark_text, font_size, font_color, position):
    """
    在图片上添加水印
    """
    try:
        # 打开图片
        image = Image.open(image_path).convert("RGBA")
        width, height = image.size
        
        # 创建水印图层
        watermark_layer = Image.new("RGBA", image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(watermark_layer)
        
        # 尝试使用系统默认字体，如果失败则使用默认字体
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", font_size)
            except:
                font = ImageFont.load_default()
        
        # 计算文本尺寸
        bbox = draw.textbbox((0, 0), watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # 根据位置参数计算水印位置
        positions = {
            'top-left': (10, 10),
            'top-center': ((width - text_width) // 2, 10),
            'top-right': (width - text_width - 10, 10),
            'middle-left': (10, (height - text_height) // 2),
            'center': ((width - text_width) // 2, (height - text_height) // 2),
            'middle-right': (width - text_width - 10, (height - text_height) // 2),
            'bottom-left': (10, height - text_height - 10),
            'bottom-center': ((width - text_width) // 2, height - text_height - 10),
            'bottom-right': (width - text_width - 10, height - text_height - 10)
        }
        
        x, y = positions.get(position, positions['bottom-right'])
        
        # 绘制水印文字
        draw.text((x, y), watermark_text, font=font, fill=font_color)
        
        # 合并图层
        watermarked_image = Image.alpha_composite(image, watermark_layer)
        
        # 转换回RGB模式以支持JPEG格式
        if image_path.lower().endswith(('.jpg', '.jpeg')):
            watermarked_image = watermarked_image.convert("RGB")
        
        return watermarked_image
    except Exception as e:
        print(f"处理图片 {image_path} 时出错: {e}")
        return None

def process_images_in_directory(directory_path, font_size, font_color, position):
    """
    处理目录中的所有图片文件
    """
    # 支持的图片格式
    supported_formats = ('.jpg', '.jpeg', '.png', '.tiff', '.bmp')
    
    # 创建水印目录
    watermark_dir = os.path.join(directory_path, f"{os.path.basename(directory_path)}_watermark")
    os.makedirs(watermark_dir, exist_ok=True)
    
    # 遍历目录中的所有文件
    processed_count = 0
    for filename in os.listdir(directory_path):
        if filename.lower().endswith(supported_formats):
            image_path = os.path.join(directory_path, filename)
            
            # 获取EXIF时间信息
            watermark_text = get_exif_datetime(image_path)
            if not watermark_text:
                print(f"警告: 无法从 {filename} 获取拍摄时间，跳过处理")
                continue
            
            # 添加水印
            watermarked_image = add_watermark_to_image(
                image_path, watermark_text, font_size, font_color, position
            )
            
            if watermarked_image:
                # 保存水印图片
                output_path = os.path.join(watermark_dir, filename)
                watermarked_image.save(output_path)
                print(f"已处理: {filename} -> {output_path}")
                processed_count += 1
    
    print(f"处理完成，共处理 {processed_count} 张图片")

def parse_color(color_string):
    """
    解析颜色字符串，支持十六进制和RGB格式
    """
    if color_string.startswith('#'):
        # 十六进制颜色
        color_string = color_string[1:]
        if len(color_string) == 6:
            return tuple(int(color_string[i:i+2], 16) for i in (0, 2, 4)) + (255,)
        elif len(color_string) == 8:
            return tuple(int(color_string[i:i+2], 16) for i in (0, 2, 4, 6))
    elif color_string.count(',') == 2 or color_string.count(',') == 3:
        # RGB或RGBA格式
        values = [int(x.strip()) for x in color_string.split(',')]
        if len(values) == 3:
            return tuple(values) + (255,)
        elif len(values) == 4:
            return tuple(values)
    
    raise argparse.ArgumentTypeError(f"无效的颜色格式: {color_string}。请使用十六进制(#RRGGBB[AA])或RGB(R,G,B)格式")

def main():
    parser = argparse.ArgumentParser(description="为图片添加基于EXIF拍摄时间的水印")
    parser.add_argument("directory", help="图片文件夹路径")
    parser.add_argument("-s", "--font-size", type=int, default=36, help="字体大小 (默认: 36)")
    parser.add_argument("-c", "--color", type=parse_color, default=(255, 255, 255, 128), 
                        help="字体颜色，支持十六进制(#RRGGBB[AA])或RGB(R,G,B)格式 (默认: #FFFFFF80)")
    parser.add_argument("-p", "--position", 
                        choices=['top-left', 'top-center', 'top-right', 
                                'middle-left', 'center', 'middle-right',
                                'bottom-left', 'bottom-center', 'bottom-right'],
                        default='bottom-right', help="水印位置 (默认: bottom-right)")
    
    args = parser.parse_args()
    
    # 检查目录是否存在
    if not os.path.isdir(args.directory):
        print(f"错误: 目录 '{args.directory}' 不存在")
        return
    
    print(f"开始处理目录: {args.directory}")
    print(f"字体大小: {args.font_size}")
    print(f"字体颜色: {args.color}")
    print(f"水印位置: {args.position}")
    
    process_images_in_directory(args.directory, args.font_size, args.color, args.position)

if __name__ == "__main__":
    main()