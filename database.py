import json
import os
import struct
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any
HEADER_SIZE = 128
MAGIC_NUMBER = b'UFC2025'
RECORD_FORMAT = 'i50s50s12s50s50s10s50s'
RECORD_SIZE = struct.calcsize(RECORD_FORMAT)


class HashIndex:
    def __init__(self, size=1000):
        self.size = size
        self.table = [None] * size
        self.collisions = 0

    def _hash(self, key, attempt=0):
        if isinstance(key, str):
            key_hash = 0
            for char in key:
                key_hash = (key_hash * 31 + ord(char)) % self.size
            key = key_hash

        h1 = key % self.size
        h2 = 1 + (key % (self.size - 1))
        return (h1 + attempt * h2) % self.size

    def add(self, key, value):
        attempt = 0
        while attempt < self.size:
            index = self._hash(key, attempt)
            if self.table[index] is None:
                self.table[index] = (key, [value])
                return True
            elif self.table[index][0] == key:
                if value not in self.table[index][1]:
                    self.table[index][1].append(value)
                return True
            self.collisions += 1
            attempt += 1
        return False

    def get(self, key):
        attempt = 0
        while attempt < self.size:
            index = self._hash(key, attempt)
            item = self.table[index]
            if item is None:
                return []
            elif item[0] == key:
                return item[1]
            attempt += 1
        return []

    def remove(self, key, value):
        attempt = 0
        while attempt < self.size:
            index = self._hash(key, attempt)
            if self.table[index] is None:
                return False
            elif self.table[index][0] == key:
                if value in self.table[index][1]:
                    self.table[index][1].remove(value)
                    if not self.table[index][1]:
                        self.table[index] = None
                    return True
                return False
            attempt += 1
        return False

    def get_all_keys(self):
        keys = []
        for item in self.table:
            if item is not None:
                keys.append(item[0])
        return keys

    def get_all_values(self):
        values = []
        for item in self.table:
            if item is not None:
                values.extend(item[1])
        return list(set(values))


class DataBase:
    def __init__(self):
        self.current_db = None
        self.hash_id_index =HashIndex(1000)
        self.hash_fighter_1_index = HashIndex(1000)
        self.hash_fighter_2_index = HashIndex(1000)
        self.hash_location_index = HashIndex(1000)
        self.hash_event_index = HashIndex(1000)
        self.hash_winner_index = HashIndex(1000)
        self.hash_date_index = HashIndex(1000)
        self.metadata = {}
        self.free_positions = []

    def create_db(self, name: str) -> bool:
        try:
            os.makedirs('data', exist_ok=True)
            with open(f'data/{name}.bin','wb') as f:
                header = struct.pack('7s50si', MAGIC_NUMBER, name.encode('utf-8'), 0)
                f.write(header.ljust(HEADER_SIZE, b'\x00'))

            self.current_db = name
            self.hash_id_index = HashIndex(1000)
            self.hash_fighter_1_index = HashIndex(1000)
            self.hash_fighter_2_index = HashIndex(1000)
            self.hash_location_index = HashIndex(1000)
            self.hash_event_index = HashIndex(1000)
            self.hash_winner_index = HashIndex(1000)
            self.hash_date_index = HashIndex(1000)
            self.free_positions = []
            self.metadata = {
                'name': name,
                'created_at': datetime.now().isoformat(),
                'record_count': 0,
                'last_update': datetime.now().isoformat(),
                'file_format': 'binary',
                'record_size': RECORD_SIZE,
                'header_size': HEADER_SIZE
            }
            self._save_metadata()
            print(f"Data base {name} has been created successfully")
            return True
        except Exception as e:
            print(f"Failed: {e}")
            return False

    def open_db(self, name: str) -> bool:
        try:
            if not os.path.exists(f'data/{name}.bin'):
                print(f"Data base {name} is not found")
                return False
            with open(f'data/{name}.bin', 'rb') as f:
                magic = f.read(7)
                if magic != MAGIC_NUMBER:
                    print("Wrong format")
                    return False
            self.current_db = name
            if os.path.exists(f'data/{name}_meta.json'):
                with open(f'data/{name}_meta.json', 'r',encoding='utf-8') as f:
                    self.metadata = json.load(f)
            else:
                self.metadata = {
                    'name': name,
                    'created_at': datetime.now().isoformat(),
                    'record_count': 0,
                    'file_format': 'binary'
                }
            self._load_indexes()
            print(f"Data base {name} has been opened successfully")
            return True
        except Exception as e:
            print(f"Failed: {e}")
            return False

    def delete_db(self, name: str) -> bool:
        try:
            files_to_delete = [
                f'data/{name}.bin',
                f'data/{name}_meta.json',
                f'data/{name}_backup.json',
                f'data/{name}_hash_index.json',
                f'data/{name}_free_positions.json'
            ]
            success = True
            for f_path in files_to_delete:
                if os.path.exists(f_path):
                    try:
                        os.remove(f_path)
                        print(f"File {f_path} has been deleted successfully")
                    except Exception as e:
                        print(f"Failed for {f_path}: {e}")
                        success = False
            if self.current_db == name:
                self.current_db = None
                self.hash_id_index = HashIndex(1000)
                self.hash_fighter_1_index = HashIndex(1000)
                self.hash_fighter_2_index = HashIndex(1000)
                self.hash_location_index = HashIndex(1000)
                self.hash_event_index = HashIndex(1000)
                self.hash_winner_index = HashIndex(1000)
                self.hash_date_index = HashIndex(1000)
                self.metadata = {}
                self.free_positions = []
            if success:
                print(f"Data base {name} has been deleted successfully")
            return success
        except Exception as e:
            print(f"Failed: {e}")
            return False

    def clear_db(self) -> bool:
        if not self.current_db:
            print("Data base is not opened")
            return False
        try:
            with open(f'data/{self.current_db}.bin', 'wb') as f:
                header = struct.pack('7s50si', MAGIC_NUMBER, self.current_db.encode('utf-8'), 0)
                f.write(header.ljust(HEADER_SIZE, b'\x00'))
            self.hash_id_index = HashIndex(1000)
            self.hash_fighter_1_index = HashIndex(1000)
            self.hash_fighter_2_index = HashIndex(1000)
            self.hash_location_index = HashIndex(1000)
            self.hash_event_index = HashIndex(1000)
            self.hash_winner_index = HashIndex(1000)
            self.hash_date_index = HashIndex(1000)
            self.free_positions = []
            self.metadata['record_count'] = 0
            self.metadata['last_update'] = datetime.now().isoformat()
            self._save_metadata()
            self._save_indexes()
            print(f"Data base {self.current_db} has been cleaned successfully")
            return True
        except Exception as e:
            print(f"Failed: {e}")
            return False

    def save_db(self) -> bool:
        if not self.current_db:
            print("Data base is not opened")
            return False
        try:
            self._save_metadata()
            self._save_indexes()
            print(f"Data base {self.current_db} has been saved successfully")
            return True
        except Exception as e:
            print(f"Failed: {e}")
            return False

    def add_record(self, record_data: Dict) -> bool:
        if not self.current_db:
            print("Data base is not opened")
            return False
        record_id = record_data['id']
        if self.hash_id_index.get(record_id) is not None:
            return False
        position = self._get_next_record_position()
        binary_data = self._record_to_binary(record_data)
        with open(f'data/{self.current_db}.bin', 'r+b') as f:
            f.seek(position)
            f.write(binary_data)
        self._update_all_indexes(record_id, position, record_data)
        self.metadata['record_count'] += 1
        self.metadata['last_update'] = datetime.now().isoformat()
        self._update_file_header()
        self._save_indexes()
        return True

    def delete_record(self, field_name: str, field_value: Any) -> str:
        if not self.current_db:
            return "Data base is not opened"
        deleted_count = 0
        if field_name == 'id':
            record_id = field_value
            positions = self.hash_id_index.get(record_id)
            if positions:
                position = positions[0] if positions else None
                if position and self._remove_single_record(record_id, position):
                    deleted_count = 1
        else:
            record_ids = self._find_ids_by_field(field_name, field_value)
            for record_id in record_ids:
                positions = self.hash_id_index.get(record_id)
                if positions:
                    position = positions[0]
                    if position and self._remove_single_record(record_id, position):
                        deleted_count += 1

        if deleted_count > 0:
            self.metadata['record_count'] -= deleted_count
            self._update_file_header()
            self._save_indexes()
            return f"Success, number of deleted records: {deleted_count}"
        else:
            return "No deleted records"

    def search_records(self, field_name: str, field_value: Any) -> List[Dict]:
        if not self.current_db:
            print("Data base is not opened")
            return []
        record_ids = self._find_ids_by_field(field_name, field_value)
        records = []
        for record_id in record_ids:
            record = self.get_record_by_id(record_id)
            if record:
                records.append(record)

        return records

    def update_record(self, record_id: int, updates: Dict) -> bool:
        positions = self.hash_id_index.get(record_id)
        if not positions:
            return False
        position = positions[0]
        current_record = self.get_record_by_id(record_id)
        if not current_record:
            return False
        updated_record = {**current_record, **updates}
        if 'id' in updates and updates['id'] != record_id:
            if self.hash_id_index.get(updates['id']) is not None:
                return False
        self._remove_from_all_indexes(record_id, current_record)
        binary_data = self._record_to_binary(updated_record)
        with open(f'data/{self.current_db}.bin', 'r+b') as f:
            f.seek(position)
            f.write(binary_data)
        if 'id' in updates:
            self.hash_id_index.remove(record_id)
            self.hash_id_index.add(updates['id'], position)
            record_id = updates['id']

        self._update_all_indexes(record_id, position, updated_record)
        self._save_indexes()
        return True

    def create_backup(self, backup_name: str) -> bool:
        if not self.current_db:
            print("Data base is not opened")
            return False
        try:
            os.makedirs('backups', exist_ok=True)
            backup_dir = f'backups/{backup_name}'
            os.makedirs(backup_dir, exist_ok=True)
            files_to_backup = [
                f'data/{self.current_db}.bin',
                f'data/{self.current_db}_meta.json',
                f'data/{self.current_db}_indexes.json',
                f'data/{self.current_db}_hash_index.json'
            ]

            for file_path in files_to_backup:
                if os.path.exists(file_path):
                    shutil.copy2(file_path, f'{backup_dir}/{os.path.basename(file_path)}')
            backup_meta = {
                'backup_name': backup_name,
                'timestamp': datetime.now().isoformat(),
                'original_db': self.current_db,
                'record_count': self.metadata['record_count']
            }

            with open(f'{backup_dir}/backup_meta.json', 'w') as f:
                json.dump(backup_meta, f, indent=2)

            print(f"Backup '{backup_name}' has been created successfully")
            return True

        except Exception as e:
            print(f"Failed: {e}")
            return False

    def restore_from_backup(self, backup_name: str) -> bool:
        try:
            backup_dir = f'backups/{backup_name}'
            if not os.path.exists(backup_dir):
                print(f"Backup {backup_name} is not found")
                return False
            with open(f'{backup_dir}/backup_meta.json', 'r') as f:
                backup_meta = json.load(f)
            original_db = backup_meta['original_db']

            files_to_restore = [
                f'{original_db}.bin',
                f'{original_db}_meta.json',
                f'{original_db}_indexes.json',
                f'{original_db}_hash_index.json'
            ]
            for file_name in files_to_restore:
                src_path = f'{backup_dir}/{file_name}'
                dst_path = f'data/{file_name}'
                if os.path.exists(src_path):
                    shutil.copy2(src_path, dst_path)
            success = self.open_db(original_db)
            if success:
                print(f"Data base has been successfully restored from {backup_name}")
            return success

        except Exception as e:
            print(f"Failed: {e}")
            return False


    def _record_to_binary(record: Dict) -> bytes:
        return (struct.pack(
            RECORD_FORMAT,
            record['id'],
            record.get('location', '').encode('utf-8'),
            record.get('event_name', '').encode('utf-8'),
            record.get('date', '').encode('utf-8'),
            record.get('fighter_1_name', '').encode('utf-8'),
            record.get('fighter_2_name', '').encode('utf-8'),
            record.get('fight_time', '').encode('utf-8'),
            record.get('winner', '').encode('utf-8')
        ))

    def _binary_to_record(binary_data: bytes) -> Dict:
        data = struct.unpack(RECORD_FORMAT, binary_data)
        return {
            'id': data[0],
            'location': data[1].decode('utf-8').strip('\x00'),
            'event_name': data[2].decode('utf-8').strip('\x00'),
            'date': data[3].decode('utf-8').strip('\x00'),
            'fighter_1_name': data[4].decode('utf-8').strip('\x00'),
            'fighter_2_name': data[5].decode('utf-8').strip('\x00'),
            'fight_time': data[6].decode('utf-8').strip('\x00'),
            'winner': data[7].decode('utf-8').strip('\x00')
        }

    def _get_next_record_position(self) -> int:
        if self.free_positions:
            return self.free_positions.pop()
        else:
            file_size = os.path.getsize(f'data/{self.current_db}.bin')
            return file_size

    def _update_file_header(self):
        with open(f'data/{self.current_db}.bin', 'r+b') as f:
            f.seek(57)
            f.write(struct.pack('i', self.metadata['record_count']))

    def get_record_by_id(self, record_id: int) -> Optional[Dict]:
        positions = self.hash_id_index.get(record_id)
        if not positions:
            return None
        try:
            position = positions[0]
            with open(f'data/{self.current_db}.bin', 'rb') as f:
                f.seek(position)
                binary_data = f.read(RECORD_SIZE)
                return self.binary_to_record(binary_data)
        except Exception as e:
            print(f"Failed: {e}")
            return None

    def _find_ids_by_field(self, field_name: str, field_value: Any) -> List[int]:
        if field_name == 'id':
            return [field_value] if self.hash_id_index.get(field_value) else []
        elif field_name == 'location':
            return self.hash_location_index.get(field_value)
        elif field_name == 'event_name':
            return self.hash_event_index.get(field_value)
        elif field_name == 'fighter_1_name':
            return self.hash_fighter_1_index.get(field_value)
        elif field_name == 'fighter_2_name':
            return self.hash_fighter_2_index.get(field_value)
        elif field_name == 'winner':
            return self.hash_winner_index.get(field_value)
        elif field_name == 'date':
            return self.hash_date_index.get(field_value)
        else:
            return []

    def _update_all_indexes(self, record_id: int, position: int, record_data: Dict):
        self.hash_id_index.add(record_id, position)
        location = record_data.get('location', '')
        if location:
            self.hash_location_index.add(location, record_id)
        event = record_data.get('event_name', '')
        if event:
            self.hash_event_index.add(event, record_id)

        fighter_1 = record_data.get('fighter_1_name', '')
        if fighter_1:
            self.hash_fighter_1_index.add(fighter_1, record_id)

        fighter_2 = record_data.get('fighter_2_name', '')
        if fighter_2:
            self.hash_fighter_2_index.add(fighter_2, record_id)

        winner = record_data.get('winner', '')
        if winner:
            self.hash_winner_index.add(winner, record_id)

        date = record_data.get('date', '')
        if date:
            self.hash_date_index.add(date, record_id)

    def _remove_from_all_indexes(self, record_id: int, record_data: Dict):
        location = record_data.get('location', '')
        if location:
            self.hash_location_index.remove(location, record_id)
        winner = record_data.get('winner', '')
        if winner:
            self.hash_winner_index.remove(winner, record_id)

        date = record_data.get('date', '')
        if date:
            self.hash_date_index.remove(date, record_id)

        event = record_data.get('event_name', '')
        if event:
            self.hash_event_index.remove(event, record_id)

        fighter_1 = record_data.get('fighter_1_name', '')
        if fighter_1:
            self.hash_fighter_1_index.remove(fighter_1, record_id)

        fighter_2 = record_data.get('fighter_2_name', '')
        if fighter_2:
            self.hash_fighter_2_index.remove(fighter_2, record_id)

    def _remove_single_record(self, record_id: int, position: int) -> bool:
        record = self.get_record_by_id(record_id)
        if not record:
            return False
        self.hash_id_index.remove(record_id)
        self._remove_from_all_indexes(record_id, record)
        self.free_positions.append(position)
        return True

    def _save_indexes(self) -> bool:
        if not self.current_db:
            print("Data base is not opened")
            return False
        try:
            indexes_data = {
                'hash_id_index': {
                    'size': self.hash_id_index.size,
                    'collisions': self.hash_id_index.collisions,
                    'table': self.hash_id_index.table
                },
                'hash_location_index': {
                    'size': self.hash_location_index.size,
                    'collisions': self.hash_location_index.collisions,
                    'table': self.hash_location_index.table
                },
                'hash_event_index': {
                    'size': self.hash_event_index.size,
                    'collisions': self.hash_event_index.collisions,
                    'table': self.hash_event_index.table
                },
                'hash_fighter_1_index': {
                    'size': self.hash_fighter_1_index.size,
                    'collisions': self.hash_fighter_1_index.collisions,
                    'table': self.hash_fighter_1_index.table
            },
                'hash_fighter_2_index': {
                    'size': self.hash_fighter_2_index.size,
                    'collisions': self.hash_fighter_2_index.collisions,
                    'table': self.hash_fighter_2_index.table
            },
                'hash_winner_index': {
                    'size': self.hash_winner_index.size,
                    'collisions': self.hash_winner_index.collisions,
                    'table': self.hash_winner_index.table
            },
                'hash_date_index': {
                    'size': self.hash_date_index.size,
                    'collisions': self.hash_date_index.collisions,
                    'table': self.hash_date_index.table
                },
                'free_positions': self.free_positions
            }
            with open(f'data/{self.current_db}_indexes.json', 'w', encoding='utf-8') as f:
                json.dump(indexes_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Failed: {e}")
            return False

    def _load_indexes(self) -> bool:
        if not self.current_db:
            print("Data base is not opened")
            return False
        try:
            if os.path.exists(f'data/{self.current_db}_indexes.json'):
                with open(f'data/{self.current_db}_indexes.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._restore_hash_index(self.hash_id_index, data.get('hash_id_index', {}))
                    self._restore_hash_index(self.hash_location_index, data.get('hash_location_index', {}))
                    self._restore_hash_index(self.hash_event_index, data.get('hash_event_index', {}))
                    self._restore_hash_index(self.hash_fighter_1_index, data.get('hash_fighter_1_index', {}))
                    self._restore_hash_index(self.hash_fighter_2_index, data.get('hash_fighter_2_index', {}))
                    self._restore_hash_index(self.hash_winner_index, data.get('hash_winner_index', {}))
                    self._restore_hash_index(self.hash_date_index, data.get('hash_date_index', {}))
                    self.free_positions = data.get('free_positions', [])
        except Exception as e:
            print(f"Failed: {e}")
            return False

    def _rebuild_hash_index(self):
        self.hash_id_index = HashIndex(1000)
        try:
            with open(f'data/{self.current_db}.bin', 'rb') as f:
                f.seek(HEADER_SIZE)

                while True:
                    position = f.tell()
                    binary_data = f.read(RECORD_SIZE)
                    if not binary_data or len(binary_data) < RECORD_SIZE:
                        break
                    record = self.binary_to_record(binary_data)
                    self.hash_id_index.add(record['id'], position)

        except Exception as e:
            print(f"Failed: {e}")
            return False

    def _restore_hash_index(self, hash_index, data):
        if data:
            hash_index.size = data.get('size', 1000)
            hash_index.collisions = data.get('collisions', 0)
            hash_index.table = data.get('table', [None] * hash_index.size)

    def _save_metadata(self):
        if self.current_db:
            try:
                with open(f'data/{self.current_db}_meta.json', 'w', encoding='utf-8') as f:
                    json.dump(self.metadata, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"Failed: {e}")

    def get_database_info(self):
        if not self.current_db:
            return {'error': 'No database opened'}

        info = {
            'name': self.current_db,
            'record_count': self.metadata.get('record_count', 0),
            'created_at': self.metadata.get('created_at', 'N/A'),
            'last_update': self.metadata.get('last_update', 'N/A'),
            'hash_collisions': self.hash_id_index.collisions +
                               self.hash_location_index.collisions +
                               self.hash_event_index.collisions +
                               self.hash_fighter_1_index.collisions +
                               self.hash_fighter_2_index.collisions +
                               self.hash_winner_index.collisions +
                               self.hash_date_index.collisions
        }
        return info

