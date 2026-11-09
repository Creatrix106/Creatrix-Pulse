import datetime as dt
import io

import numpy as np
import openpyxl
import pandas as pd
import pytest
from app.services.ingestion.cleaner import clean_table, parse_dates, parse_numeric, to_text
from app.services.ingestion.errors import IngestionError
from app.services.ingestion.fields import normalise_header, resolve_mapping, suggest_mapping
from app.services.ingestion.profile import build_columns, build_filter_options, infer_type
from app.services.ingestion.reader import read_table

LIMITS = dict(max_rows=10**6, max_columns=200, max_uncompressed_bytes=400 * 2**20)
S = lambda values: pd.Series(values, dtype="str")  # noqa: E731


def read(data, name="a.csv", **limits):
    return read_table(data.encode() if isinstance(data, str) else data, name, **{**LIMITS, **limits})


def clean(csv, mapping=None, *, dayfirst=True):
    parsed = read(csv)
    resolved = resolve_mapping(list(parsed.frame.columns), mapping)
    return clean_table(parsed, resolved, auto_mapped=not mapping, default_dayfirst=dayfirst)


def error_of(csv, mapping=None, name="a.csv"):
    action = (lambda: clean(csv, mapping)) if name == "a.csv" else (lambda: read(csv, name))
    with pytest.raises(IngestionError) as info:
        action()
    return str(info.value)


def xlsx(rows, sheets=None):
    book = openpyxl.Workbook()
    sheet = book.active
    for row in rows:
        sheet.append(row)
    for title, extra in (sheets or {}).items():
        other = book.create_sheet(title)
        for row in extra:
            other.append(row)
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


# ------------------------------------------------------------------------------------------- reader
class TestReader:
    def test_encodings_and_delimiters(self):
        for label, data in {
            "utf-8 BOM": "\ufeffDate,Product,Revenue\n2026-01-05,Café,10\n".encode(),
            "cp1252 (Excel on Windows)": "Date,Product,Revenue\n2026-01-05,Café,10\n".encode("cp1252"),
            "semicolon": b"Date;Product;Revenue\n2026-01-05;Cafe;10\n",
            "tab": b"Date\tProduct\tRevenue\n2026-01-05\tCafe\t10\n",
            "pipe": b"Date|Product|Revenue\n2026-01-05|Cafe|10\n",
        }.items():
            parsed = read(data)
            assert list(parsed.frame.columns) == ["Date", "Product", "Revenue"], label
            assert len(parsed.frame) == 1, label
        assert read("\ufeffDate,Product,Revenue\n2026-01-05,Café,10\n".encode()).frame["Product"].iloc[0] == "Café"
        assert read("Date,Product,Revenue\n2026-01-05,Café,10\n".encode("cp1252")).frame["Product"].iloc[0] == "Café"

    def test_commas_inside_quoted_headers_do_not_confuse_delimiter_detection(self):
        parsed = read('"Sales, Total";Date\n10;2026-01-01\n')
        assert list(parsed.frame.columns) == ["Sales, Total", "Date"]

    def test_only_truly_empty_cells_are_missing(self):
        frame = read("Date,Region,Product\n2026-01-01,NA,N/A\n2026-01-02,,null\n2026-01-03,None,-\n").frame
        assert frame["Region"].tolist()[0] == "NA"  # North America must survive pandas' default NA list
        assert pd.isna(frame["Region"].iloc[1])
        assert frame["Product"].tolist() == ["N/A", "null", "-"]
        assert frame["Region"].iloc[2] == "None"

    def test_headers_are_cleaned_like_the_browser_does(self):
        frame = read("  Order Date ,,Revenue,Revenue\n2026-01-01,x,1,2\n").frame
        assert list(frame.columns) == ["Order Date", "Column 2", "Revenue", "Revenue.1"] or list(frame.columns) == [
            "Order Date", "Column 2", "Revenue", "Revenue (2)",
        ]  # fmt: skip
        assert len(set(frame.columns)) == 4

    def test_extra_fields_never_shift_columns_silently(self):
        """Regression: pandas' defaults used the surplus first field as an implicit index, so every value moved
        one column to the left (Date would receive the Product, Product the Revenue...)."""
        for csv in ("a,b\n1,2,3\n", "a,b\n1,2,3\n4,5,6\n", "a,b\n1,2\n3,4,5\n"):
            with pytest.raises(IngestionError, match="more values than the header row"):
                read(csv)

    def test_a_trailing_comma_on_every_row_is_harmless(self):  # a common export quirk
        frame = read("a,b\n1,2,\n3,4,\n").frame
        assert frame.values.tolist() == [["1", "2"], ["3", "4"]]

    def test_short_rows_are_padded_not_rejected(self):
        assert read("a,b,c\n1,2\n3\n").frame.isna().sum().tolist() == [0, 1, 2]

    def test_row_numbers_are_spreadsheet_numbers(self):
        assert read("A,B\n1,2\n3,4\n").row_numbers.tolist() == [2, 3]

    @pytest.mark.parametrize(
        ("data", "name", "fragment"),
        [
            (b"", "a.csv", "The file is empty."),
            (b"x", "a.pdf", "Unsupported file type"),
            (b"PK\x03\x04rest-of-zip", "a.csv", "Excel/zip archive with a .csv extension"),
            (bytes.fromhex("d0cf11e0a1b11ae1") + b"..", "a.csv", "legacy Excel workbook with a .csv extension"),
            (b"a,b\n\x00\x01\x02", "a.csv", "binary data"),
            (b"a,b\n1,2,3\n", "a.csv", "Some rows have more values than the header row"),
            (b"a,b\n1,2\n3,4,5\n", "a.csv", "Line 3 has more values than the header row"),
            (b"a,b\n1,2\n", "a.xlsx", "corrupted or isn't a real Excel workbook"),
            (b"a,b\n1,2\n", "a.xls", "has an .xls extension but isn't an Excel workbook"),
        ],
    )
    def test_malformed_files_get_actionable_messages(self, data, name, fragment):
        with pytest.raises(IngestionError, match=fragment):
            read(data, name)

    def test_size_limits(self):
        with pytest.raises(IngestionError, match="more than 3 rows"):
            read("A\n1\n2\n3\n4\n", max_rows=3)
        with pytest.raises(IngestionError, match="2 columns; the limit is 1"):
            read("A,B\n1,2\n", max_columns=1)
        read("A\n1\n2\n3\n", max_rows=3)  # exactly at the limit is fine

    def test_zip_bomb_guard_rejects_workbooks_that_inflate_too_far(self):
        data = xlsx([["Date", "Product", "Revenue"], ["2026-01-01", "x", 1]])
        with pytest.raises(IngestionError, match="more data than we can process"):
            read(data, "bomb.xlsx", max_uncompressed_bytes=100)
        assert len(read(data, "ok.xlsx").frame) == 1

    def test_first_sheet_with_data_is_used(self):
        data = xlsx([[]], sheets={"Data": [["Date", "Product", "Revenue"], [dt.datetime(2026, 1, 1), "x", 1]]})
        assert list(read(data, "book.xlsx").frame.columns) == ["Date", "Product", "Revenue"]

    def test_excel_cells_keep_their_types(self):
        data = xlsx([["Order ID", "Date", "Revenue"], [10001, dt.datetime(2026, 1, 5, 14, 30), 1299.5]])
        frame = read(data, "t.xlsx").frame
        assert pd.api.types.is_datetime64_any_dtype(frame["Date"])
        assert pd.api.types.is_numeric_dtype(frame["Revenue"])


# -------------------------------------------------------------------------------------------- mapping
class TestMapping:
    @pytest.mark.parametrize(
        ("headers", "expected"),
        [
            (["Date", "Product", "Revenue"], {"date": "Date", "product": "Product", "revenue": "Revenue"}),
            (
                [
                    "Order Date",
                    "Item Name",
                    "Total Sales",
                    "Qty",
                    "Invoice No",
                    "Department",
                    "State",
                    "Client",
                    "COGS",
                ],
                {
                    "date": "Order Date",
                    "product": "Item Name",
                    "revenue": "Total Sales",
                    "quantity": "Qty",
                    "orderId": "Invoice No",
                    "category": "Department",
                    "region": "State",
                    "customer": "Client",
                    "cost": "COGS",
                },
            ),
            (["created_at", "SKU", "Amount"], {"date": "created_at", "product": "SKU", "revenue": "Amount"}),
            (
                ["Total", "Total Cost", "Date", "Product"],
                {"revenue": "Total", "cost": "Total Cost", "date": "Date", "product": "Product"},
            ),
            (["Notes", "Foo"], {}),
        ],
    )
    def test_suggestions_match_the_frontend_alias_lists(self, headers, expected):
        assert suggest_mapping(headers) == expected

    def test_normalisation(self):
        assert normalise_header("  Order-Date (UTC) ") == "order date utc"
        assert normalise_header("Order_ID") == "order id"

    def test_each_header_is_claimed_once(self):
        assert suggest_mapping(["Date", "Product", "Amount", "Total"]) == {
            "date": "Date",
            "product": "Product",
            "revenue": "Amount",
        }

    def test_explicit_mapping_is_respected_exactly(self):
        headers = ["Date", "Product", "Revenue", "Category", "Cost"]
        explicit = {"date": "Date", "product": "Product", "revenue": "Revenue"}  # user left Category/Cost unmapped
        assert resolve_mapping(headers, explicit) == explicit

    def test_loose_header_matching(self):
        assert resolve_mapping(["Date ", "P", "R"], {"date": "date", "product": "P", "revenue": "R"})["date"] == "Date "

    def test_mapping_errors(self):
        with pytest.raises(IngestionError, match="isn't in the file"):
            resolve_mapping(["A", "B", "C"], {"date": "A", "product": "B", "revenue": "Nope"})
        with pytest.raises(IngestionError, match="required to generate analytics"):
            resolve_mapping(["A", "B", "C"], {"date": "A", "product": "B"})
        with pytest.raises(IngestionError, match="mapped to both"):
            resolve_mapping(["A", "B"], {"date": "A", "product": "B", "revenue": "B"})
        with pytest.raises(IngestionError, match=r"“Order date”, “Product” and “Revenue”"):
            resolve_mapping(["X", "Y"], None)


# ----------------------------------------------------------------------------------------------- dates
class TestDates:
    def days(self, values, **kw):
        result = parse_dates(S(values), **kw)
        return [None if pd.isna(v) else v.strftime("%Y-%m-%d") for v in result]

    def test_iso_dates_keep_the_calendar_day_written_in_the_file(self):
        assert (
            self.days(
                [
                    "2026-01-05",
                    "2026-1-5",
                    "2026-01-05T10:30:00",
                    "2026-01-05 10:30:00+05:30",
                    "2026-01-05T23:59:59-08:00",
                ]
            )
            == ["2026-01-05"] * 5
        )

    def test_ambiguous_dates_default_to_day_first_unless_the_column_proves_otherwise(self):
        assert self.days(["03/04/2026"], dayfirst_default=True) == ["2026-04-03"]
        assert self.days(["03/04/2026"], dayfirst_default=False) == ["2026-03-04"]
        assert self.days(["03/04/2026", "25/03/2026"], dayfirst_default=False) == [
            "2026-04-03",
            "2026-03-25",
        ]  # 25 is a day
        assert self.days(["03/04/2026", "03/25/2026"], dayfirst_default=True) == [
            "2026-03-04",
            "2026-03-25",
        ]  # 25 is a day

    def test_other_separators_two_digit_years_and_text_months(self):
        assert self.days(["3-4-26", "03.04.2026", "5-Jan-2026", "Jan 5, 2026", "5 January 2026", "20260105"]) == [
            "2026-04-03", "2026-04-03", "2026-01-05", "2026-01-05", "2026-01-05", "2026-01-05",
        ]  # fmt: skip
        assert self.days(["1/1/68", "1/1/69"]) == ["2068-01-01", "1969-01-01"]  # POSIX two-digit-year pivot

    def test_unreadable_values_become_missing_rather_than_guessed(self):
        assert self.days(["2026-02-30", "13/13/2026", "garbage", None, "1850-01-01", "2200-01-01", ""]) == [None] * 7

    def test_excel_serial_numbers_and_compact_integers(self):
        assert [v.strftime("%Y-%m-%d") for v in parse_dates(pd.Series([46027.0, 46028.5]))] == [
            "2026-01-05",
            "2026-01-06",
        ]
        assert [v.strftime("%Y-%m-%d") for v in parse_dates(pd.Series([20260105, 20260106]))] == [
            "2026-01-05",
            "2026-01-06",
        ]

    def test_datetime_columns_pass_through_normalised(self):
        series = pd.Series(pd.to_datetime(["2026-01-05 22:00", "2026-01-06 01:00"]).tz_localize("UTC"))
        assert [v.strftime("%Y-%m-%d") for v in parse_dates(series)] == ["2026-01-05", "2026-01-06"]  # wall-clock date
        mixed = pd.Series([pd.Timestamp("2026-01-05"), "2026-01-06", dt.date(2026, 1, 7)], dtype=object)
        assert [v.strftime("%Y-%m-%d") for v in parse_dates(mixed)] == ["2026-01-05", "2026-01-06", "2026-01-07"]


# --------------------------------------------------------------------------------------------- numbers
class TestNumbers:
    def test_formats_people_really_use(self):
        cases = {
            "1299.50": 1299.5, "₹1,299.50": 1299.5, "12,34,567.89": 1234567.89, "(50.00)": -50.0, "Rs. 100": 100.0,
            "INR 2,500": 2500.0, "$ 12": 12.0, "-€5": -5.0, "1e3": 1000.0, "  7  ": 7.0, "\u00a01,000\u00a0": 1000.0, ".5": 0.5,
        }  # fmt: skip
        result = parse_numeric(S(list(cases)))
        assert result.tolist() == list(cases.values())

    def test_decimal_commas_are_rejected_instead_of_silently_misread(self):
        bad = ["12,5", "1.234,56", "1,23", "1,2345", "abc", "-", "50%", "inf", "nan", "5."]
        assert parse_numeric(S(bad)).isna().all()

    def test_numeric_and_object_columns(self):
        assert parse_numeric(pd.Series([1, 2.5, np.nan, np.inf])).isna().tolist() == [False, False, True, True]
        assert parse_numeric(pd.Series([1299.5, "₹1,050.00", None], dtype=object)).tolist()[:2] == [1299.5, 1050.0]
        assert parse_numeric(pd.Series([True, False])).isna().all()  # a boolean is not an amount

    def test_always_float64(self):
        assert parse_numeric(S(["1", "2"])).dtype == "float64"

    def test_numeric_ids_do_not_gain_a_decimal_point(self):
        assert to_text(pd.Series([10001.0, 10002.5, np.nan, 7])).tolist()[:2] == ["10001", "10002.5"]
        assert to_text(pd.Series([10001, 10002])).tolist() == ["10001", "10002"]


# --------------------------------------------------------------------------------------------- cleaning
class TestCleaning:
    FULL = (
        "Order ID,Order Date,Product,Category,Region,Customer,Qty,Revenue,Cost\n"
        'A1,2026-01-05,Tee,Apparel,NA,C1,2,"₹1,299.50",800\n'
        "A2,15/01/2026,Lamp,,South,,1,(50.00),20\n"
        ",,,,,,,,\n"
        "A3,2026-01-06,,Apparel,,C2,3,100,30\n"
    )

    def test_a_realistic_messy_file(self):
        result = clean(self.FULL)
        frame = result.frame
        assert list(frame.columns) == [
            "row_number", "order_date", "order_id", "product", "category", "region", "customer", "quantity", "revenue", "cost",
        ]  # fmt: skip
        assert len(frame) == 3  # the empty row is ignored...
        assert sorted(frame["row_number"].tolist()) == [2, 3, 5]  # ...but rows keep their file position
        assert frame["order_date"].dt.strftime("%Y-%m-%d").tolist() == [
            "2026-01-05",
            "2026-01-06",
            "2026-01-15",
        ]  # sorted by date
        assert frame["revenue"].tolist() == [
            1299.5,
            100.0,
            -50.0,
        ]  # currency symbol, thousands comma, accounting negative
        assert frame["region"].tolist() == ["NA", "Unknown", "South"]  # "NA" is North America; blank gets a label
        assert frame["category"].tolist() == ["Apparel", "Apparel", "Uncategorized"]
        assert frame["product"].tolist() == ["Tee", "Unknown product", "Lamp"]
        assert frame["customer"].isna().tolist() == [False, False, True]  # a customer cannot be invented
        assert result.capabilities.customers and result.capabilities.cost and result.capabilities.regions
        assert (result.date_from, result.date_to) == (dt.date(2026, 1, 5), dt.date(2026, 1, 15))

    def test_dtypes_are_stable_whatever_the_values(self):
        for text in (
            "Date,Product,Revenue,Qty,Cost\n2026-01-05,Tee,10,2,4\n",
            "Date,Product,Revenue,Qty,Cost\n2026-01-05,Tee,10.5,2.5,4.5\n",
        ):
            frame = clean(text).frame
            assert {c: str(t) for c, t in frame.dtypes.items()} == {
                "row_number": "int32", "order_date": "datetime64[us]", "order_id": "str", "product": "str", "category": "str",
                "region": "str", "customer": "str", "quantity": "float64", "revenue": "float64", "cost": "float64",
            }  # fmt: skip

    def test_missing_optional_columns_get_neutral_defaults(self):
        result = clean("Date,Product,Revenue\n2026-01-05,Tee,10\n")
        frame = result.frame
        assert frame["quantity"].tolist() == [1.0]  # every row is one unit
        assert frame["order_id"].isna().all() and frame["cost"].isna().all() and frame["category"].isna().all()
        assert not (result.capabilities.customers or result.capabilities.cost or result.capabilities.regions)

    @pytest.mark.parametrize(
        ("csv", "fragment"),
        [
            (
                "Date,Product,Revenue\n2026-01-05,Tee,10\nnot-a-date,Lamp,5\n,Bag,3\n",
                "date column “Date” could not be read in 2 rows (e.g. row 3: “not-a-date”; row 4: empty)",
            ),
            (
                "Date,Product,Revenue\n2026-01-05,Tee,abc\n",
                "revenue column “Revenue” is empty, invalid or out of range in 1 row (e.g. row 2: “abc”)",
            ),
            ("Date,Product,Revenue\n2026-01-05,Tee,\n", "in 1 row (e.g. row 2: empty)"),
            ("Date,Product,Revenue\n2026-01-05,Tee,1e15\n", "out of range"),
            ("Date,Product,Revenue\n2026-01-05,Tee,12,5\n", "Some rows have more values than the header row"),
            ("Date,Product,Revenue\n,,\n", "The file has no data rows."),
            ("Date,Product,Revenue\n", "The file has no data rows."),
        ],
    )
    def test_strict_validation_messages(self, csv, fragment):
        assert fragment in error_of(csv)

    def test_optional_numeric_columns_are_strict_when_the_user_mapped_them(self):
        csv = "Date,Product,Revenue,Cost\n2026-01-05,Tee,10,x\n"
        mapping = {"date": "Date", "product": "Product", "revenue": "Revenue", "cost": "Cost"}
        assert "cost column “Cost” is empty, invalid or out of range in 1 row" in error_of(csv, mapping)

    def test_but_a_bad_auto_detected_column_is_dropped_instead_of_failing_the_upload(self):
        result = clean("Date,Product,Revenue,Cost,Units\n2026-01-05,Tee,10,x,pcs\n")  # no mapping (Excel path)
        assert "cost" not in result.mapping and "quantity" not in result.mapping
        assert not result.capabilities.cost

    def test_a_mapped_but_completely_empty_text_column_behaves_as_unmapped(self):
        result = clean("Date,Product,Revenue,Category,Customer\n2026-01-05,Tee,10,,\n")
        assert "category" not in result.mapping and not result.capabilities.customers
        assert result.frame["category"].isna().all()

    def test_negative_and_zero_amounts_are_legitimate(self):  # returns / refunds / free items
        frame = clean("Date,Product,Revenue,Qty\n2026-01-05,Tee,-25,-1\n2026-01-06,Gift,0,1\n").frame
        assert frame["revenue"].tolist() == [-25.0, 0.0] and frame["quantity"].tolist() == [-1.0, 1.0]

    def test_excel_values_survive_typing(self):
        data = xlsx(
            [
                ["Order ID", "Order Date", "Product", "Qty", "Revenue"],
                [10001, dt.datetime(2026, 1, 5, 14, 30), "Tee", 2, 1299.5],
                [10002, dt.date(2026, 1, 6), "Lamp", 1, "₹1,050.00"],
                [None, None, None, None, None],
            ]
        )
        parsed = read(data, "t.xlsx")
        result = clean_table(
            parsed, resolve_mapping(list(parsed.frame.columns), None), auto_mapped=True, default_dayfirst=True
        )
        assert result.frame["order_id"].tolist() == ["10001", "10002"]  # not "10001.0"
        assert result.frame["order_date"].dt.strftime("%Y-%m-%d").tolist() == ["2026-01-05", "2026-01-06"]
        assert result.frame["revenue"].tolist() == [1299.5, 1050.0]


# ------------------------------------------------------------------------------------------ profiling
class TestProfile:
    @pytest.mark.parametrize(
        ("values", "expected"),
        [
            (["2026-01-05", "2026-1-6", "5/1/2026", "2026-01-05T10:00:00"], "date"),
            (["12", "₹1,299.50", "-3", ".5"], "number"),
            (["true", "FALSE", "Yes", "no"], "boolean"),
            (["Tee", "Lamp", "Bag"], "string"),
            (["1", "2", "3", "4", "5", "6", "7", "8", "9", "x"], "string"),  # exactly 90% is not "more than 90%"
            (["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "x"], "number"),  # 11/12 > 90%
            ([None, None], "string"),
        ],
    )
    def test_type_inference_follows_the_browsers_rules(self, values, expected):
        assert infer_type(pd.Series(values, dtype="str")) == expected

    def test_typed_columns(self):
        assert infer_type(pd.Series([True, False])) == "boolean"
        assert infer_type(pd.Series(pd.to_datetime(["2026-01-01"]))) == "date"
        assert infer_type(pd.Series([1.5, 2])) == "number"

    def test_columns_listing_and_filter_options(self):
        parsed = read("Date,Product,Revenue,Notes\n2026-01-05,Tee,10,hi\n")
        columns = build_columns(parsed, {"date": "Date", "product": "Product", "revenue": "Revenue"})
        assert columns == [
            {"name": "Date", "type": "date", "mappedTo": "date"},
            {"name": "Product", "type": "string", "mappedTo": "product"},
            {"name": "Revenue", "type": "number", "mappedTo": "revenue"},
            {"name": "Notes", "type": "string"},  # unmapped columns are listed too, like the mock does
        ]
        frame = clean("Date,Product,Revenue,Category,Region\n2026-01-05,A,1,Zed,N\n2026-01-06,B,1,Alpha,N\n").frame
        assert build_filter_options(frame) == {"categories": ["Alpha", "Zed"], "regions": ["N"]}
