from django.shortcuts import render
from django.utils import timezone
from django.db import connection
from uuid import uuid4
from django.http import JsonResponse
from django.db.utils import DatabaseError
from datetime import datetime, timedelta
from .utils import *
import calendar
import json

# TRANSACTION_DATA = []

def langganan_paket(request):

    with connection.cursor() as cursor:
        cursor.execute("SELECT jenis, harga FROM paket")
        rows = parse(cursor)
        for row in rows:
            row['harga'] = f"Rp{row['harga']:,.0f}".replace(",", ".")
    context = {

        'paket' : rows,
    }

    return render(request, 'langganan_paket.html', context)

# def langganan_paket(request):
#     user = request.session.get('user')

#     paket_data = get_paket_data()
#     return render(request, 'langganan_paket.html', {'paket_data': paket_data, 'user': user})

def add_months(start_date, months):
    month = start_date.month - 1 + months
    year = start_date.year + month // 12
    month = month % 12 + 1
    day = min(start_date.day, [31,
                               29 if year % 4 == 0 and not year % 100 == 0 or year % 400 == 0 else 28,
                               31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return datetime(year, month, day)


def pembayaran(request, jenis):
    with connection.cursor() as cursor:
        get_paket = f"""
            SELECT * FROM PAKET WHERE jenis = '{jenis}';
        """
        cursor.execute(get_paket)
        jenis_paket = parse(cursor)

    for row in jenis_paket:
        row['harga'] = f"Rp{row['harga']:,.0f}".replace(",", ".")

    metode_bayar = ['Transfer Bank', 'Kartu Kredit', 'E-Wallet']

    context = {
        'paket' : jenis_paket,
        'metode_bayar' : metode_bayar
    }

    return render(request, 'pembayaran.html', context)

def riwayat_transaksi(request):
    with connection.cursor() as cursor:
        query_riwayat = f"""
        SELECT * FROM TRANSACTION WHERE email = '{request.session['email']}'
        """
        cursor.execute(query_riwayat)
        riwayat = parse(cursor)
    # transactions = sorted(TRANSACTION_DATA, key=lambda x: x['timestamp_dimulai'], reverse=True)
    context = {
        'riwayat': riwayat,
    }
    return render(request, 'riwayat_transaksi.html', context)

def pembayaran_paket(request):
    if request.method == "POST":
        # user = context_user_getter(request)
        jenis_paket = request.POST.get('jenis')
        metode_bayar = request.POST.get('metode_bayar')

        try:
            cursor = connection.cursor()
            id_transaksi = str(uuid4())
            timestamp_dimulai = datetime.now()
            nominal = 0
            if jenis_paket == '1 BULAN':
                    timestamp_berakhir = add_months(timestamp_dimulai, 1)
                    cursor.execute("""SELECT harga FROM PAKET WHERE jenis = '1 BULAN'""")
                    nominal = cursor.fetchone()[0]
            elif jenis_paket == '3 BULAN':
                    timestamp_berakhir = add_months(timestamp_dimulai, 3)
                    cursor.execute("""SELECT harga FROM paket WHERE jenis = '3 BULAN';""")
                    nominal = cursor.fetchone()[0]
            elif jenis_paket == '6 BULAN':
                    timestamp_berakhir = add_months(timestamp_dimulai, 6)
                    cursor.execute("""SELECT harga FROM PAKET WHERE jenis = '6 BULAN';""")
                    nominal = cursor.fetchone()[0]
            else:
                    timestamp_berakhir = add_months(timestamp_dimulai, 12)
                    cursor.execute("""SELECT harga FROM PAKET WHERE jenis = '1 TAHUN';""")
                    nominal = cursor.fetchone()[0]
                
            # print("Start date:", timestamp_dimulai)
            # print("End date:", timestamp_berakhir)
            # print("Jenis paket:", jenis_paket)
            # print("Nominal:", nominal)

            cursor.execute(f"""INSERT INTO TRANSACTION VALUES ('{id_transaksi}','{jenis_paket}','{request.session['email']}','{timestamp_dimulai}','{timestamp_berakhir}','{metode_bayar}',{nominal});""")
            cursor.execute("""DELETE FROM NONPREMIUM WHERE email = %s""", [request.session['email']])
            connection.commit()

            user_data = json.loads(request.session['user'])[0]
            user_data['status_langganan'] = 'Premium'
            request.session['user'] = json.dumps([user_data])

            return JsonResponse({'success': True, 'message': 'Paket berhasil dibeli'})
        except DatabaseError as error:
            print(f"Database error occurred: {error}")
            connection.rollback()
            return JsonResponse({'success': False, 'message': 'Paket gagal dibeli'})


# FITUR SEARCH
# data coba
# SONGS = [
#     {"title": "Love is in the air", "artist": "Artist1", "type": "SONG"},
#     {"title": "What is love", "artist": "Artist2", "type": "SONG"},
#     {"title": "Love is Blind Pod", "podcaster": "Podcaster1", "type": "PODCAST"},
#     {"title": "90s Love Songs", "creator": "User1", "type": "USER PLAYLIST"},
# ]

def search(request):
    query = request.GET.get('query', '')

    with connection.cursor() as cursor:
        sql_query_song = f"""SELECT K.judul, A.nama, K.id FROM SONG S, ARTIST AR, AKUN A, KONTEN K 
            WHERE S.id_konten = K.id 
            AND S.id_artist = AR.id 
            AND AR.email_akun = A.email 
            AND K.judul ILIKE '%{query}%';
            """
        cursor.execute(sql_query_song)
        song_result = parse(cursor)

        sql_query_podcast = f"""
            SELECT K.judul, A.nama, K.id FROM PODCAST P, AKUN A, KONTEN K 
            WHERE P.id_konten = K.id 
            AND P.email_podcaster = A.email
            and K.judul ILIKE '%{query}%';
            """
        cursor.execute(sql_query_podcast)
        podcast_result = parse(cursor)

        sql_query_playlist=f"""
            SELECT UP.judul, A.nama, UP.id_playlist, UP.email_pembuat
            FROM USER_PLAYLIST UP, AKUN A
            WHERE UP.email_pembuat = A.email and UP.judul ILIKE '%{query}%';
            """
        cursor.execute(sql_query_playlist)
        user_playlist_result = parse(cursor)
    
    context = {
        'query' : query,
        'song_result' : song_result,
        'podcast_result' : podcast_result,
        'user_playlist_result' : user_playlist_result
    }

    print(user_playlist_result)

    return render(request, 'search.html', context)


#FITUR DOWNLOAD
def downloaded_songs(request):
    with connection.cursor() as cursor:
        email_download = request.session['email']
        sql_query_download = f"""
            SELECT K.judul, A.nama, K.id, DS.email_downloader, DS.email_downloader FROM DOWNLOADED_SONG DS, SONG S, ARTIST AR, KONTEN K, AKUN A 
            WHERE DS.email_downloader = '{email_download}'
            AND DS.id_song = S.id_konten 
            AND S.id_konten = K.id 
            AND S.id_artist = AR.id 
            AND AR.email_akun = A.email;
        """
        cursor.execute(sql_query_download)
        downloaded_songs = parse(cursor)
        context = {
            'downloaded_songs' : downloaded_songs
        }

    return render(request, 'downloaded_songs.html', context)

def delete_song(request, id_song, email_downloader):
    if request.method == 'POST':
        with connection.cursor() as cursor:
            cursor.execute(f"""DELETE FROM DOWNLOADED_SONG WHERE id_song = '{id_song}' AND email_downloader = '{email_downloader}'""")
            connection.commit()
            cursor.execute(f"""SELECT judul FROM KONTEN WHERE id = '{id_song}';""")
            delete_song = parse(cursor)
        return JsonResponse({'success': True, 'message': f'Berhasil menghapus lagu dengan judul "{delete_song[0].get("judul")}" dari daftar unduhan!'})

