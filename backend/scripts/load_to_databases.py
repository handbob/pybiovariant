import os
from cyvcf2 import VCF
import psycopg2
from pymongo import MongoClient

def load_vcf(file_path, frequency_threshold=0.01, batch_size=1000):
    """Loads and filters variants from a VCF file."""
    vcf_reader = VCF(file_path)
    filtered_variants = []
    total_records = 0

    for record in vcf_reader:
        total_records += 1
        if total_records % 10000 == 0:
            print(f"Processed {total_records} records...")

        af = record.INFO.get('AF', 0)

        if isinstance(af, tuple):
            af = af[0]

        if af >= frequency_threshold:
            filtered_variants.append(record)

        # Process in batches to avoid memory overload
        if len(filtered_variants) >= batch_size:
            yield filtered_variants
            filtered_variants = []

    # Yield any remaining records
    if filtered_variants:
        yield filtered_variants

def store_in_postgresql(variants):
    """Stores variants in PostgreSQL."""
    conn = psycopg2.connect(database="biovariant", user="postgres", password="postgres", host="localhost", port="5432")
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS variants
                      (chromosome VARCHAR, position INTEGER, ref_allele VARCHAR, alt_allele VARCHAR);''')

    postgres_data = [(variant.CHROM, variant.POS, variant.REF, variant.ALT[0]) for variant in variants]
    args_str = ','.join(cursor.mogrify("(%s,%s,%s,%s)", variant).decode('utf-8') for variant in postgres_data)

    cursor.execute(f"INSERT INTO variants (chromosome, position, ref_allele, alt_allele) VALUES {args_str}")

    conn.commit()
    cursor.close()
    conn.close()

# def store_in_mongodb(variants):
#     """Stores variants in MongoDB."""
#     client = MongoClient('localhost', 27017)
#     db = client['biovariant']
#     collection = db['variants']
#
#     mongo_data = [{
#         'chromosome': variant.CHROM,
#         'position': variant.POS,
#         'ref_allele': variant.REF,
#         'alt_allele': variant.ALT[0],
#         'info': dict(variant.INFO)
#     } for variant in variants]

    # collection.insert_many(mongo_data)

if __name__ == "__main__":
    # Use absolute path for the VCF file
    vcf_file = os.path.abspath('backend/data/ALL.chrY.phase3_integrated_v2b.20130502.genotypes.vcf.gz')

    print(f"Using VCF file at: {vcf_file}")

    # Load and process variants in batches
    for variant_batch in load_vcf(vcf_file):
        store_in_postgresql(variant_batch)
        # store_in_mongodb(variant_batch)
        print(f"Stored batch of {len(variant_batch)} variants.")
