"""
Script tạo 992 users còn lại (từ ID 9 đến 1000)
Chạy script này trong Django shell hoặc management command

Usage:
    python manage.py shell < create_users.py
    hoặc
    python manage.py create_bulk_users
"""

import os
import django
from datetime import datetime, timedelta
import random

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from api.accounts.models import Profile

# Faker để tạo dữ liệu giả
try:
    from faker import Faker
    fake = Faker(['en_US', 'vi_VN'])
except ImportError:
    fake = None

# =========================
# CẤU HÌNH
# =========================
EXISTING_USERS = 8
TOTAL_USERS = 1000
USERS_TO_CREATE = TOTAL_USERS - EXISTING_USERS

# Vietnamese data
VIETNAM_CITIES = [
    'Hà Nội', 'TP. Hồ Chí Minh', 'Đà Nẵng', 'Hải Phòng', 'Cần Thơ',
    'Biên Hòa', 'Nha Trang', 'Huế', 'Vũng Tàu', 'Quy Nhơn'
]

LAST_NAMES = ['Nguyễn', 'Trần', 'Lê', 'Phạm', 'Hoàng', 'Huỳnh', 'Phan', 'Vũ', 'Võ', 'Đặng']
MIDDLE_NAMES = ['Văn', 'Thị', 'Hữu', 'Đức', 'Minh', 'Thanh', 'Anh', 'Quốc', 'Bảo', 'Gia']
FIRST_NAMES_MALE = ['Hùng', 'Dũng', 'Nam', 'Tuấn', 'Khoa', 'Long', 'Đạt', 'Hải', 'Thành', 'Phong']
FIRST_NAMES_FEMALE = ['Hương', 'Linh', 'Nga', 'Mai', 'Lan', 'Hà', 'Thảo', 'Trang', 'Ngọc', 'Vy']

# =========================
# HELPER FUNCTIONS
# =========================
def generate_username(index):
    """Tạo username duy nhất"""
    prefixes = ['user', 'member', 'customer', 'buyer', 'client']
    return f"{random.choice(prefixes)}{index:04d}"

def generate_email(username):
    """Tạo email từ username"""
    domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com']
    return f"{username}@{random.choice(domains)}"

def generate_vietnamese_name():
    """Tạo tên tiếng Việt"""
    gender = random.choice(['male', 'female'])
    last = random.choice(LAST_NAMES)
    middle = random.choice(MIDDLE_NAMES)
    first = random.choice(FIRST_NAMES_MALE if gender == 'male' else FIRST_NAMES_FEMALE)
    return f"{last} {middle} {first}", gender

def generate_phone():
    """Tạo số điện thoại Việt Nam"""
    prefixes = ['090', '091', '094', '098', '032', '033', '034', '035', '036', '037', '038', '039']
    return f"{random.choice(prefixes)}{random.randint(1000000, 9999999)}"

def generate_birthday():
    """Tạo ngày sinh (18-70 tuổi)"""
    today = datetime.now()
    age = random.randint(18, 70)
    birth_year = today.year - age
    birth_month = random.randint(1, 12)
    birth_day = random.randint(1, 28)
    return datetime(birth_year, birth_month, birth_day).date()

def generate_bio():
    """Tạo bio đơn giản"""
    bios = [
        'Yêu thích công nghệ và đổi mới',
        'Đam mê sản phẩm điện tử',
        'Luôn cập nhật xu hướng mới',
        'Thích khám phá công nghệ mới',
        'Người dùng công nghệ nhiệt tình',
        '',  # Some users have no bio
        '',
    ]
    return random.choice(bios)

# =========================
# MAIN FUNCTION
# =========================
@transaction.atomic
def create_bulk_users(stdout):
    """Tạo hàng loạt users"""
    
    stdout.write("="*60)
    stdout.write(f"🚀 Bắt đầu tạo {USERS_TO_CREATE} users...")
    stdout.write(f"📊 Database hiện có: {User.objects.count()} users")
    stdout.write("="*60)
    
    users_created = 0
    profiles_created = 0
    errors = []
    
    try:
        for i in range(EXISTING_USERS + 1, TOTAL_USERS + 1):
            try:
                # Generate data
                username = generate_username(i)
                email = generate_email(username)
                
                # Check duplicate
                while User.objects.filter(username=username).exists():
                    username = f"{username}_{random.randint(100, 999)}"
                
                # Create User
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password='defaultpass123',
                    first_name=fake.first_name() if fake else f"First{i}",
                    last_name=fake.last_name() if fake else f"Last{i}",
                    is_active=True,
                    is_staff=False,
                    is_superuser=False,
                    date_joined=datetime.now() - timedelta(days=random.randint(0, 365))
                )
                users_created += 1
                
                # Create Profile
                vietnamese_name, gender = generate_vietnamese_name()
                Profile.objects.create(
                    user=user,
                    name=vietnamese_name,
                    bio=generate_bio(),
                    gender=gender,
                    birthday=generate_birthday(),
                    phone=generate_phone(),
                    email=email,
                    personal_info=''
                )
                profiles_created += 1
                
                # Progress
                if i % 100 == 0:
                    stdout.write(f"✓ Đã tạo {users_created} users...")
                    
            except Exception as e:
                error_msg = f"Error at user {i}: {str(e)}"
                errors.append(error_msg)
                continue
        
        # Summary
        stdout.write("\n" + "="*60)
        stdout.write("✅ HOÀN THÀNH")
        stdout.write("="*60)
        stdout.write(f"👥 Users đã tạo: {users_created}/{USERS_TO_CREATE}")
        stdout.write(f"📝 Profiles đã tạo: {profiles_created}/{USERS_TO_CREATE}")
        stdout.write(f"📊 Tổng users trong DB: {User.objects.count()}")
        stdout.write(f"❌ Errors: {len(errors)}")
        
        if errors:
            stdout.write("\n⚠️  Chi tiết lỗi (10 đầu tiên):")
            for error in errors[:10]:
                stdout.write(f"   - {error}")
        
        # Verify
        stdout.write("\n🔍 Xác minh:")
        first_user = User.objects.order_by('id').first()
        last_user = User.objects.order_by('id').last()
        stdout.write(f"   - User IDs: {first_user.id} → {last_user.id}")
        stdout.write(f"   - Total Profiles: {Profile.objects.count()}")
        stdout.write("="*60)
        
        return True
        
    except Exception as e:
        stdout.write(f"\n❌ LỖI NGHIÊM TRỌNG: {str(e)}")
        raise

# =========================
# DJANGO COMMAND CLASS
# =========================
class Command(BaseCommand):
    help = 'Tạo 992 users còn lại (ID 9-1000) với Profile đầy đủ'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Xóa tất cả users từ ID 9 trở đi trước khi tạo mới',
        )

    def handle(self, *args, **options):
        # Reset if requested
        if options['reset']:
            self.stdout.write(self.style.WARNING('⚠️  Đang xóa users cũ từ ID 9...'))
            deleted = User.objects.filter(id__gt=8).delete()
            self.stdout.write(self.style.WARNING(f'🗑️  Đã xóa {deleted[0]} users'))
        
        # Create users
        self.stdout.write(self.style.NOTICE('Bắt đầu tạo users...'))
        
        try:
            success = create_bulk_users(self.stdout)
            
            if success:
                self.stdout.write(self.style.SUCCESS('\n✅ TẠO USERS THÀNH CÔNG!'))
                self.stdout.write(self.style.SUCCESS('Password mặc định: defaultpass123'))
            else:
                self.stdout.write(self.style.ERROR('\n❌ CÓ LỖI XẢY RA!'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ LỖI: {str(e)}'))
            raise