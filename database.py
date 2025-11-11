import struct
import os
import pickle
import shutil
import json
import re

RECORD_FMT = '<I10s8s50s50s30s30s30sB'
RECORD_SIZE = struct.calcsize(RECORD_FMT)

def _encode(s, length):
    b = str(s).encode('utf-8')[:length]
    return b.ljust(length, b'\x00')

def _decode(bs):
    return bs.split(b'\x00', 1)[0].decode('utf-8')

def _is_numeric_only(s: str):
    return bool(re.fullmatch(r"\d+", s.strip())) if isinstance(s, str) and s.strip() else False

def _validate_fight_time_mmss(s: str):
    if not isinstance(s, str):
        return False
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", s.strip())
    if not m:
        return False
    seconds = int(m.group(2))
    return 0 <= seconds < 60

class Record:
    __slots__ = ('id','date','fight_time','event','location','fighter_1','fighter_2','winner','active')
    def __init__(self,id:int, date:str, fight_time:str, event:str, location:str, fighter_1:str, fighter_2:str, winner:str, active=1):
        self.id = int(id)
        self.date = date
        self.fight_time = fight_time
        self.event = event
        self.location = location
        self.fighter_1 = fighter_1
        self.fighter_2 = fighter_2
        self.winner = winner
        self.active = int(active)

    def pack(self):
        return struct.pack(RECORD_FMT,
                           self.id,
                           _encode(self.date,10),
                           _encode(self.fight_time,8),
                           _encode(self.event,50),
                           _encode(self.location,50),
                           _encode(self.fighter_1,30),
                           _encode(self.fighter_2,30),
                           _encode(self.winner,30),
                           self.active)

    @classmethod
    def unpack(cls, bs):
        vals = struct.unpack(RECORD_FMT, bs)
        return cls(
            vals[0],
            _decode(vals[1]),
            _decode(vals[2]),
            _decode(vals[3]),
            _decode(vals[4]),
            _decode(vals[5]),
            _decode(vals[6]),
            _decode(vals[7]),
            vals[8]
        )

class Database:
    def __init__(self, filepath):
        self.filepath = filepath
        self.indexpath = filepath + '.idx'
        self.file = None
        self.index = {}


    def create(self, overwrite=False):
        if os.path.exists(self.filepath) and not overwrite:
            raise FileExistsError('DB file already exists')
        open(self.filepath, 'wb').close()
        self.index = {}
        self._save_index()

    def open(self):
        if not os.path.exists(self.filepath):
            raise FileNotFoundError('DB file not found')
        self.file = open(self.filepath, 'r+b')
        if os.path.exists(self.indexpath):
            with open(self.indexpath, 'rb') as f:
                self.index = pickle.load(f)
        else:
            self._rebuild_index()

    def close(self):
        if self.file:
            try:
                self.file.flush()
            except Exception:
                pass
            self.file.close()
            self.file = None
        self._save_index()

    def delete(self):
        if self.file:
            self.file.close(); self.file = None
        if os.path.exists(self.filepath): os.remove(self.filepath)
        if os.path.exists(self.indexpath): os.remove(self.indexpath)
        self.index = {}

    def clear(self):
        if self.file:
            self.file.close(); self.file = None
        open(self.filepath, 'wb').close()
        self.index = {}
        self._save_index()
        self.open()

    def save(self):
        self._save_index()
        if self.file:
            try:
                self.file.flush()
            except Exception:
                pass

    def _save_index(self):
        with open(self.indexpath, 'wb') as f:
            pickle.dump(self.index, f)

    def _rebuild_index(self):
        self.index = {}
        with open(self.filepath, 'rb') as f:
            offset = 0
            while True:
                bs = f.read(RECORD_SIZE)
                if not bs or len(bs) < RECORD_SIZE:
                    break
                rec = Record.unpack(bs)
                if rec.active:
                    self.index[rec.id] = offset
                offset += RECORD_SIZE
        self._save_index()


    def _record_equals_except_id(self, rec1: Record, rec2: Record):
        return (
            rec1.date == rec2.date and
            rec1.fight_time == rec2.fight_time and
            rec1.event == rec2.event and
            rec1.location == rec2.location and
            rec1.fighter_1 == rec2.fighter_1 and
            rec1.fighter_2 == rec2.fighter_2 and
            rec1.winner == rec2.winner
        )

    def _find_duplicate(self, newrec: Record):

        if not os.path.exists(self.filepath):
            return False
        open_mode = self.file is not None
        if not open_mode:
            f = open(self.filepath,'rb')
            try:
                while True:
                    bs = f.read(RECORD_SIZE)
                    if not bs or len(bs) < RECORD_SIZE: break
                    rec = Record.unpack(bs)
                    if rec.active and self._record_equals_except_id(rec, newrec):
                        return True
            finally:
                f.close()
            return False
        else:
            self.file.seek(0)
            while True:
                bs = self.file.read(RECORD_SIZE)
                if not bs or len(bs) < RECORD_SIZE: break
                rec = Record.unpack(bs)
                if rec.active and self._record_equals_except_id(rec, newrec):
                    return True
            return False

    def _next_id(self):
        if not self.index:
            return 1
        max_id = max(self.index.keys())
        return max_id + 1

    def _renumber_ids(self):

        if not os.path.exists(self.filepath):
            self.index = {}
            return

        need_close = False
        if self.file is None:
            self.open()
            need_close = True


        self.file.seek(0)
        offset = 0
        next_id = 1
        changes = []
        while True:
            bs = self.file.read(RECORD_SIZE)
            if not bs or len(bs) < RECORD_SIZE:
                break
            rec = Record.unpack(bs)
            if rec.active:
                if rec.id != next_id:
                    rec.id = next_id

                    self.file.seek(offset)
                    self.file.write(rec.pack())
                    self.file.flush()
                self.index[rec.id] = offset
                next_id += 1
            offset += RECORD_SIZE


        self._rebuild_index()
        if need_close:

            try:
                self.file.close()
            except Exception:
                pass
            self.file = None


    def add(self, record:Record):

        if _is_numeric_only(record.fighter_1) or _is_numeric_only(record.fighter_2) or _is_numeric_only(record.winner):
            raise ValueError('Fighter names/winner must not be numeric-only strings')
        if not _validate_fight_time_mmss(record.fight_time):
            raise ValueError('fight_time must be in MM:SS format, seconds 00-59')

        if record.winner and not (record.winner == record.fighter_1 or record.winner == record.fighter_2):
            raise ValueError('winner must be one of fighter_1 or fighter_2')


        if self.file is None:
            if not os.path.exists(self.filepath):
                open(self.filepath,'wb').close()
            self.open()


        assigned_id = self._next_id()
        if record.id != assigned_id:
            record.id = assigned_id


        if self._find_duplicate(record):
            raise ValueError('Duplicate record (identical fields except id)')


        self.file.seek(0, os.SEEK_END)
        offset = self.file.tell()
        self.file.write(record.pack())
        self.file.flush()
        self.index[record.id] = offset
        self._save_index()
        return record.id

    def _read_at(self, offset):
        if self.file is None:
            self.open()
        self.file.seek(offset)
        bs = self.file.read(RECORD_SIZE)
        if not bs or len(bs) < RECORD_SIZE:
            return None
        return Record.unpack(bs)

    def get_by_id(self, id_):
        if id_ not in self.index:
            return None
        rec = self._read_at(self.index[id_])
        if rec and rec.active:
            return rec
        return None

    def delete_by_id(self, id_):
        if id_ not in self.index:
            return 0
        offset = self.index[id_]
        if self.file is None:
            self.open()
        self.file.seek(offset)
        bs = self.file.read(RECORD_SIZE)
        rec = Record.unpack(bs)
        rec.active = 0
        self.file.seek(offset)
        self.file.write(rec.pack())
        self.file.flush()

        if id_ in self.index:
            del self.index[id_]

        self._renumber_ids()
        self._save_index()
        return 1

    def delete_by_field(self, field, value):

        count = 0
        if field == 'id':
            try:
                return self.delete_by_id(int(value))
            except Exception:
                return 0
        if self.file is None:
            self.open()
        self.file.seek(0)
        offset = 0
        while True:
            bs = self.file.read(RECORD_SIZE)
            if not bs or len(bs) < RECORD_SIZE:
                break
            rec = Record.unpack(bs)
            if rec.active and getattr(rec, field) == value:
                rec.active = 0
                self.file.seek(offset)
                self.file.write(rec.pack())
                self.file.flush()
                if rec.id in self.index:
                    del self.index[rec.id]
                count += 1
            offset += RECORD_SIZE
        if count > 0:
            self._renumber_ids()
            self._save_index()
        return count

    def search(self, field, value):
        results = []
        if field == 'id':
            try:
                rec = self.get_by_id(int(value))
            except Exception:
                return []
            if rec: results.append(rec)
            return results
        if self.file is None:
            self.open()
        self.file.seek(0)
        while True:
            bs = self.file.read(RECORD_SIZE)
            if not bs or len(bs) < RECORD_SIZE:
                break
            rec = Record.unpack(bs)
            if rec.active and getattr(rec, field) == value:
                results.append(rec)
        return results

    def edit(self, id_, **kwargs):
        if id_ not in self.index:
            raise KeyError('id not found')
        offset = self.index[id_]
        rec = self._read_at(offset)
        if not rec or not rec.active:
            raise KeyError('record inactive or not found')
        newrec = Record(rec.id, rec.date, rec.fight_time, rec.event, rec.location, rec.fighter_1, rec.fighter_2, rec.winner, rec.active)
        for k,v in kwargs.items():
            if hasattr(newrec, k) and k != 'id' and v is not None:
                setattr(newrec, k, v)

        if _is_numeric_only(newrec.fighter_1) or _is_numeric_only(newrec.fighter_2) or _is_numeric_only(newrec.winner):
            raise ValueError('Fighter names/winner must not be numeric-only strings')
        if not _validate_fight_time_mmss(newrec.fight_time):
            raise ValueError('fight_time must be in MM:SS format, seconds 00-59')
        if newrec.winner and not (newrec.winner == newrec.fighter_1 or newrec.winner == newrec.fighter_2):
            raise ValueError('winner must be one of fighter_1 or fighter_2')

        if self.file is None:
            self.open()
        self.file.seek(0)
        while True:
            bs = self.file.read(RECORD_SIZE)
            if not bs or len(bs) < RECORD_SIZE:
                break
            other = Record.unpack(bs)
            if other.active and other.id != newrec.id and self._record_equals_except_id(other, newrec):
                raise ValueError('Edit would create duplicate record (identical fields except id)')

        self.file.seek(offset)
        self.file.write(newrec.pack())
        self.file.flush()

        return newrec

    def backup(self, backup_path):

        self._save_index()
        was_open = False
        try:
            if self.file:
                try:
                    self.file.flush()
                except Exception:
                    pass
                try:
                    self.file.close()
                    was_open = True
                    self.file = None
                except Exception:
                    self.file = None
            shutil.copy2(self.filepath, backup_path)
            if os.path.exists(self.indexpath):
                shutil.copy2(self.indexpath, backup_path + '.idx')
        finally:
            try:
                if was_open:
                    self.open()
            except Exception:
                self.file = None

    def restore_from_backup(self, backup_path):
        if self.file:
            self.file.close(); self.file = None
        shutil.copy2(backup_path, self.filepath)
        if os.path.exists(backup_path + '.idx'):
            shutil.copy2(backup_path + '.idx', self.indexpath)
        else:
            self._rebuild_index()
        self.open()

    def import_json(self, json_path, id_field='id'):
        with open(json_path,'r',encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            for k in data:
                if isinstance(data[k], list):
                    data = data[k]
                    break
            else:
                return 0
        if not isinstance(data, list):
            return 0
        added = 0
        for item in data:
            try:
                rec = Record(
                    int(item.get(id_field, 0) or 0),
                    item.get('date','0000-00-00'),
                    item.get('fight_time','00:00'),
                    item.get('event',''),
                    item.get('location',''),
                    item.get('fighter_1',''),
                    item.get('fighter_2',''),
                    item.get('winner','')
                )
                self.add(rec)
                added += 1
            except Exception:
                continue
        return added

    def export_excel(self, excel_path, id_col='id'):
        try:
            import pandas as pd
        except ImportError:
            raise RuntimeError('pandas is required to export to excel')
        rows = []
        for r in self.iterate():
            rows.append({
                'id': r.id,
                'date': r.date,
                'fight_time': r.fight_time,
                'event': r.event,
                'location': r.location,
                'fighter_1': r.fighter_1,
                'fighter_2': r.fighter_2,
                'winner': r.winner
            })
        df = pd.DataFrame(rows)
        df.to_excel(excel_path, index=False)
        return len(rows)

    def iterate(self):
        if not os.path.exists(self.filepath):
            return
        if self.file is None:
            self.open()
        self.file.seek(0)
        while True:
            bs = self.file.read(RECORD_SIZE)
            if not bs or len(bs) < RECORD_SIZE:
                break
            rec = Record.unpack(bs)
            if rec.active:
                yield rec
