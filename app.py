from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect
)

from flask_cors import CORS

import boto3
import base64
import uuid

from datetime import datetime
from decimal import Decimal

from botocore.exceptions import (
    BotoCoreError,
    ClientError
)


# ============================================================
# FLASK APPLICATION
# ============================================================

app = Flask(__name__)



# ============================================================
# CORS
# ============================================================

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "http://13.206.249.209:5173",
                "http://13.206.249.209:5000"
            ]
        }
    }
)


# ============================================================
# AWS CONFIGURATION
# ============================================================

AWS_REGION = "ap-south-1"


rekognition = boto3.client(
    "rekognition",
    region_name=AWS_REGION
)


dynamodb = boto3.resource(
    "dynamodb",
    region_name=AWS_REGION
)


# ============================================================
# APPLICATION SETTINGS
# ============================================================

ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png"
}


MAX_IMAGE_SIZE = (
    10
    *
    1024
    *
    1024
)


# ============================================================
# MODULE SETTINGS
# ============================================================

FACE_MATCH_THRESHOLD = 90

LABEL_MIN_CONFIDENCE = 75

PPE_MIN_CONFIDENCE = 80

LIVENESS_THRESHOLD = 90


# ============================================================
# SMARTPRESENCE SETTINGS
# ============================================================

STUDENT_COLLECTION = (
    "smart-vision-students"
)


STUDENTS_TABLE = (
    "VisionAI-Students"
)


ATTENDANCE_TABLE = (
    "VisionAI-Attendance"
)


FACE_SEARCH_THRESHOLD = 90


students_table = dynamodb.Table(
    STUDENTS_TABLE
)


attendance_table = dynamodb.Table(
    ATTENDANCE_TABLE
)


# ============================================================
# COMMON FUNCTION
# VALIDATE IMAGE
# ============================================================

def validate_image(file):

    if not file:

        return (
            None,
            "Please select an image."
        )

    if file.filename == "":

        return (
            None,
            "Please select an image."
        )

    if "." not in file.filename:

        return (
            None,
            "Invalid image file."
        )

    extension = (
        file.filename
        .rsplit(".", 1)[-1]
        .lower()
    )

    if extension not in ALLOWED_EXTENSIONS:

        return (
            None,
            "Only JPG, JPEG and PNG images are supported."
        )

    image_bytes = file.read()

    if not image_bytes:

        return (
            None,
            "Uploaded image is empty."
        )

    if len(image_bytes) > MAX_IMAGE_SIZE:

        return (
            None,
            "Image size must be less than 10 MB."
        )

    return (
        image_bytes,
        None
    )


# ============================================================
# COMMON FUNCTION
# CREATE IMAGE PREVIEW
# ============================================================

def create_preview(
    image_bytes,
    mime_type
):

    encoded_image = (
        base64
        .b64encode(
            image_bytes
        )
        .decode(
            "utf-8"
        )
    )

    mime_type = (
        mime_type
        or
        "image/jpeg"
    )

    return (
        f"data:{mime_type};base64,"
        f"{encoded_image}"
    )


# ============================================================
# COMMON FUNCTION
# IMAGE SIZE
# ============================================================

def get_image_size_kb(
    image_bytes
):

    return round(
        len(image_bytes)
        /
        1024,
        2
    )


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ============================================================
# MODULE 1
# FACIAL INTELLIGENCE
# DetectFaces
# ============================================================

@app.route(
    "/facial-analysis",
    methods=[
        "GET",
        "POST"
    ]
)
def facial_analysis():

    if request.method == "GET":

        return render_template(
            "facial_analysis.html"
        )

    image = request.files.get(
        "image"
    )

    image_bytes, error = (
        validate_image(
            image
        )
    )

    if error:

        return render_template(
            "facial_analysis.html",
            error=error
        )

    image_preview = create_preview(
        image_bytes,
        image.mimetype
    )

    try:

        response = (
            rekognition.detect_faces(

                Image={
                    "Bytes":
                        image_bytes
                },

                Attributes=[
                    "ALL"
                ]
            )
        )

        faces = response.get(
            "FaceDetails",
            []
        )

        if not faces:

            return render_template(

                "facial_analysis.html",

                error=(
                    "No face was detected "
                    "in this image."
                ),

                image_preview=(
                    image_preview
                ),

                filename=(
                    image.filename
                ),

                image_size=(
                    get_image_size_kb(
                        image_bytes
                    )
                )
            )

        for face in faces:

            emotions = face.get(
                "Emotions",
                []
            )

            face["Emotions"] = sorted(

                emotions,

                key=lambda item:
                    item.get(
                        "Confidence",
                        0
                    ),

                reverse=True
            )

            if face["Emotions"]:

                face["TopEmotion"] = (
                    face["Emotions"][0]
                )

            else:

                face["TopEmotion"] = {
                    "Type":
                        "UNKNOWN",
                    "Confidence":
                        0
                }

        return render_template(

            "facial_analysis.html",

            faces=faces,

            face_count=len(
                faces
            ),

            image_preview=(
                image_preview
            ),

            filename=(
                image.filename
            ),

            image_size=(
                get_image_size_kb(
                    image_bytes
                )
            )
        )

    except ClientError as error:

        message = (
            error.response
            .get("Error", {})
            .get(
                "Message",
                str(error)
            )
        )

        return render_template(

            "facial_analysis.html",

            image_preview=(
                image_preview
            ),

            error=(
                "Amazon Rekognition error: "
                +
                message
            )
        )

    except BotoCoreError as error:

        return render_template(

            "facial_analysis.html",

            error=(
                "AWS connection error: "
                +
                str(error)
            )
        )

    except Exception as error:

        return render_template(

            "facial_analysis.html",

            error=(
                "Application error: "
                +
                str(error)
            )
        )


# ============================================================
# MODULE 2
# FACE COMPARISON
# CompareFaces
# ============================================================

@app.route(
    "/face-comparison",
    methods=[
        "GET",
        "POST"
    ]
)
def face_comparison():

    if request.method == "GET":

        return render_template(
            "face_comparison.html"
        )

    source_image = (
        request.files.get(
            "source_image"
        )
    )

    target_image = (
        request.files.get(
            "target_image"
        )
    )

    source_bytes, source_error = (
        validate_image(
            source_image
        )
    )

    if source_error:

        return render_template(

            "face_comparison.html",

            error=(
                "Source image: "
                +
                source_error
            )
        )

    target_bytes, target_error = (
        validate_image(
            target_image
        )
    )

    if target_error:

        return render_template(

            "face_comparison.html",

            error=(
                "Target image: "
                +
                target_error
            )
        )

    source_preview = create_preview(
        source_bytes,
        source_image.mimetype
    )

    target_preview = create_preview(
        target_bytes,
        target_image.mimetype
    )

    try:

        response = (
            rekognition.compare_faces(

                SourceImage={
                    "Bytes":
                        source_bytes
                },

                TargetImage={
                    "Bytes":
                        target_bytes
                },

                SimilarityThreshold=(
                    FACE_MATCH_THRESHOLD
                )
            )
        )

        matches = response.get(
            "FaceMatches",
            []
        )

        unmatched_faces = response.get(
            "UnmatchedFaces",
            []
        )

        source_face = response.get(
            "SourceImageFace",
            {}
        )

        best_match = None

        if matches:

            best_match = max(

                matches,

                key=lambda item:
                    item.get(
                        "Similarity",
                        0
                    )
            )

        similarity = 0

        if best_match:

            similarity = (
                best_match.get(
                    "Similarity",
                    0
                )
            )

        is_match = (

            best_match
            is not None

            and

            similarity
            >=
            FACE_MATCH_THRESHOLD
        )

        return render_template(

            "face_comparison.html",

            source_preview=(
                source_preview
            ),

            target_preview=(
                target_preview
            ),

            source_filename=(
                source_image.filename
            ),

            target_filename=(
                target_image.filename
            ),

            source_size=(
                get_image_size_kb(
                    source_bytes
                )
            ),

            target_size=(
                get_image_size_kb(
                    target_bytes
                )
            ),

            best_match=(
                best_match
            ),

            similarity=(
                similarity
            ),

            is_match=(
                is_match
            ),

            source_face=(
                source_face
            ),

            unmatched_count=len(
                unmatched_faces
            ),

            match_count=len(
                matches
            ),

            threshold=(
                FACE_MATCH_THRESHOLD
            )
        )

    except (
        rekognition
        .exceptions
        .InvalidParameterException
    ):

        return render_template(

            "face_comparison.html",

            source_preview=(
                source_preview
            ),

            target_preview=(
                target_preview
            ),

            error=(
                "Amazon Rekognition could not "
                "find a usable face in one of "
                "the uploaded images."
            )
        )

    except ClientError as error:

        message = (
            error.response
            .get("Error", {})
            .get(
                "Message",
                str(error)
            )
        )

        return render_template(

            "face_comparison.html",

            source_preview=(
                source_preview
            ),

            target_preview=(
                target_preview
            ),

            error=(
                "Amazon Rekognition error: "
                +
                message
            )
        )

    except Exception as error:

        return render_template(

            "face_comparison.html",

            error=(
                "Application error: "
                +
                str(error)
            )
        )


# ============================================================
# MODULE 3
# CELEBRITY RECOGNITION
# ============================================================

@app.route(
    "/celebrity-recognition",
    methods=[
        "GET",
        "POST"
    ]
)
def celebrity_recognition():

    if request.method == "GET":

        return render_template(
            "celebrity_recognition.html"
        )

    image = request.files.get(
        "image"
    )

    image_bytes, error = (
        validate_image(
            image
        )
    )

    if error:

        return render_template(
            "celebrity_recognition.html",
            error=error
        )

    image_preview = create_preview(
        image_bytes,
        image.mimetype
    )

    try:

        response = (
            rekognition
            .recognize_celebrities(

                Image={
                    "Bytes":
                        image_bytes
                }
            )
        )

        celebrities = response.get(
            "CelebrityFaces",
            []
        )

        unrecognized = response.get(
            "UnrecognizedFaces",
            []
        )

        celebrities = sorted(

            celebrities,

            key=lambda item:
                item.get(
                    "MatchConfidence",
                    0
                ),

            reverse=True
        )

        return render_template(

            "celebrity_recognition.html",

            image_preview=(
                image_preview
            ),

            filename=(
                image.filename
            ),

            image_size=(
                get_image_size_kb(
                    image_bytes
                )
            ),

            celebrities=(
                celebrities
            ),

            celebrity_count=len(
                celebrities
            ),

            unrecognized_count=len(
                unrecognized
            ),

            total_faces=(
                len(
                    celebrities
                )
                +
                len(
                    unrecognized
                )
            )
        )

    except Exception as error:

        return render_template(

            "celebrity_recognition.html",

            error=(
                "Application error: "
                +
                str(error)
            )
        )


# ============================================================
# MODULE 4
# LABEL DETECTION
# ============================================================

@app.route(
    "/label-detection",
    methods=[
        "GET",
        "POST"
    ]
)
def label_detection():

    if request.method == "GET":

        return render_template(
            "label_detection.html"
        )

    image = request.files.get(
        "image"
    )

    image_bytes, error = (
        validate_image(
            image
        )
    )

    if error:

        return render_template(
            "label_detection.html",
            error=error
        )

    image_preview = create_preview(
        image_bytes,
        image.mimetype
    )

    try:

        response = (
            rekognition.detect_labels(

                Image={
                    "Bytes":
                        image_bytes
                },

                MaxLabels=30,

                MinConfidence=(
                    LABEL_MIN_CONFIDENCE
                ),

                Features=[
                    "GENERAL_LABELS"
                ]
            )
        )

        labels = response.get(
            "Labels",
            []
        )

        labels = sorted(

            labels,

            key=lambda item:
                item.get(
                    "Confidence",
                    0
                ),

            reverse=True
        )

        categories = set()

        total_instances = 0

        for label in labels:

            total_instances += len(
                label.get(
                    "Instances",
                    []
                )
            )

            for category in (
                label.get(
                    "Categories",
                    []
                )
            ):

                name = category.get(
                    "Name"
                )

                if name:

                    categories.add(
                        name
                    )

        top_label = (
            labels[0]
            if labels
            else None
        )

        return render_template(

            "label_detection.html",

            image_preview=(
                image_preview
            ),

            filename=(
                image.filename
            ),

            image_size=(
                get_image_size_kb(
                    image_bytes
                )
            ),

            labels=(
                labels
            ),

            label_count=len(
                labels
            ),

            total_instances=(
                total_instances
            ),

            categories=sorted(
                categories
            ),

            category_count=len(
                categories
            ),

            top_label=(
                top_label
            ),

            min_confidence=(
                LABEL_MIN_CONFIDENCE
            )
        )

    except Exception as error:

        return render_template(

            "label_detection.html",

            error=(
                "Application error: "
                +
                str(error)
            )
        )


# ============================================================
# MODULE 5
# TEXT DETECTION
# ============================================================

@app.route(
    "/text-detection",
    methods=[
        "GET",
        "POST"
    ]
)
def text_detection():

    if request.method == "GET":

        return render_template(
            "text_detection.html"
        )

    image = request.files.get(
        "image"
    )

    image_bytes, error = (
        validate_image(
            image
        )
    )

    if error:

        return render_template(
            "text_detection.html",
            error=error
        )

    image_preview = create_preview(
        image_bytes,
        image.mimetype
    )

    try:

        response = (
            rekognition.detect_text(

                Image={
                    "Bytes":
                        image_bytes
                }
            )
        )

        detections = response.get(
            "TextDetections",
            []
        )

        lines = [

            item

            for item
            in detections

            if item.get(
                "Type"
            )
            ==
            "LINE"
        ]

        words = [

            item

            for item
            in detections

            if item.get(
                "Type"
            )
            ==
            "WORD"
        ]

        extracted_text = "\n".join(

            item.get(
                "DetectedText",
                ""
            )

            for item
            in lines
        )

        confidence_values = [

            item.get(
                "Confidence",
                0
            )

            for item
            in detections
        ]

        average_confidence = 0
        highest_confidence = 0

        if confidence_values:

            average_confidence = (

                sum(
                    confidence_values
                )

                /

                len(
                    confidence_values
                )
            )

            highest_confidence = max(
                confidence_values
            )

        top_word = None

        if words:

            top_word = max(

                words,

                key=lambda item:
                    item.get(
                        "Confidence",
                        0
                    )
            )

        return render_template(

            "text_detection.html",

            image_preview=(
                image_preview
            ),

            filename=(
                image.filename
            ),

            image_size=(
                get_image_size_kb(
                    image_bytes
                )
            ),

            detections=(
                detections
            ),

            lines=(
                lines
            ),

            words=(
                words
            ),

            line_count=len(
                lines
            ),

            word_count=len(
                words
            ),

            detection_count=len(
                detections
            ),

            extracted_text=(
                extracted_text
            ),

            average_confidence=(
                average_confidence
            ),

            highest_confidence=(
                highest_confidence
            ),

            top_word=(
                top_word
            )
        )

    except Exception as error:

        return render_template(

            "text_detection.html",

            error=(
                "Application error: "
                +
                str(error)
            )
        )


# ============================================================
# MODULE 6
# PPE DETECTION
# ============================================================

@app.route(
    "/ppe-detection",
    methods=[
        "GET",
        "POST"
    ]
)
def ppe_detection():

    if request.method == "GET":

        return render_template(
            "ppe_detection.html"
        )

    image = request.files.get(
        "image"
    )

    image_bytes, error = (
        validate_image(
            image
        )
    )

    if error:

        return render_template(
            "ppe_detection.html",
            error=error
        )

    image_preview = create_preview(
        image_bytes,
        image.mimetype
    )

    try:

        response = (
            rekognition
            .detect_protective_equipment(

                Image={
                    "Bytes":
                        image_bytes
                },

                SummarizationAttributes={

                    "MinConfidence":
                        PPE_MIN_CONFIDENCE,

                    "RequiredEquipmentTypes": [
                        "HEAD_COVER",
                        "FACE_COVER",
                        "HAND_COVER"
                    ]
                }
            )
        )

        raw_persons = response.get(
            "Persons",
            []
        )

        summary = response.get(
            "Summary",
            {}
        )

        persons_with_required = (
            summary.get(
                "PersonsWithRequiredEquipment",
                []
            )
        )

        persons_without_required = (
            summary.get(
                "PersonsWithoutRequiredEquipment",
                []
            )
        )

        persons_indeterminate = (
            summary.get(
                "PersonsIndeterminate",
                []
            )
        )

        person_reports = []

        for person in raw_persons:

            person_id = person.get(
                "Id"
            )

            head_cover = False
            face_cover = False
            hand_cover = False

            equipment_report = []

            for body_part in (
                person.get(
                    "BodyParts",
                    []
                )
            ):

                for equipment in (
                    body_part.get(
                        "EquipmentDetections",
                        []
                    )
                ):

                    equipment_type = (
                        equipment.get(
                            "Type",
                            ""
                        )
                    )

                    covers = (
                        equipment.get(
                            "CoversBodyPart",
                            {}
                        )
                    )

                    is_covering = (
                        covers.get(
                            "Value",
                            False
                        )
                    )

                    equipment_report.append({

                        "type":
                            equipment_type,

                        "confidence":
                            equipment.get(
                                "Confidence",
                                0
                            ),

                        "covers":
                            is_covering,

                        "coverage_confidence":
                            covers.get(
                                "Confidence",
                                0
                            ),

                        "body_part":
                            body_part.get(
                                "Name",
                                ""
                            )
                    })

                    if (
                        equipment_type
                        ==
                        "HEAD_COVER"

                        and

                        is_covering
                    ):

                        head_cover = True

                    elif (
                        equipment_type
                        ==
                        "FACE_COVER"

                        and

                        is_covering
                    ):

                        face_cover = True

                    elif (
                        equipment_type
                        ==
                        "HAND_COVER"

                        and

                        is_covering
                    ):

                        hand_cover = True

            if (
                person_id
                in
                persons_with_required
            ):

                status = "COMPLIANT"

            elif (
                person_id
                in
                persons_without_required
            ):

                status = (
                    "NON_COMPLIANT"
                )

            else:

                status = (
                    "INDETERMINATE"
                )

            person_reports.append({

                "id":
                    person_id,

                "confidence":
                    person.get(
                        "Confidence",
                        0
                    ),

                "status":
                    status,

                "head_cover":
                    head_cover,

                "face_cover":
                    face_cover,

                "hand_cover":
                    hand_cover,

                "equipment":
                    equipment_report
            })

        total_people = len(
            raw_persons
        )

        compliant_people = len(
            persons_with_required
        )

        compliance_score = 0

        if total_people:

            compliance_score = (

                compliant_people
                /
                total_people

            ) * 100

        return render_template(

            "ppe_detection.html",

            image_preview=(
                image_preview
            ),

            filename=(
                image.filename
            ),

            image_size=(
                get_image_size_kb(
                    image_bytes
                )
            ),

            persons=(
                person_reports
            ),

            total_people=(
                total_people
            ),

            compliant_people=(
                compliant_people
            ),

            non_compliant_people=len(
                persons_without_required
            ),

            indeterminate_people=len(
                persons_indeterminate
            ),

            compliance_score=(
                compliance_score
            ),

            min_confidence=(
                PPE_MIN_CONFIDENCE
            ),

            model_version=(
                response.get(
                    "ProtectiveEquipmentModelVersion",
                    "Unknown"
                )
            )
        )

    except Exception as error:

        return render_template(

            "ppe_detection.html",

            error=(
                "Application error: "
                +
                str(error)
            )
        )


# ============================================================
# MODULE 7
# LIVEVERIFY FRONTEND
# ============================================================

@app.route(
    "/face-liveness"
)
def face_liveness():

    return redirect(
        "/liveverify/"
    )


# ============================================================
# MODULE 7
# CREATE LIVENESS SESSION
# ============================================================

@app.route(
    "/api/liveness/create-session",
    methods=[
        "POST"
    ]
)
def create_liveness_session():

    try:

        response = (
            rekognition
            .create_face_liveness_session()
        )

        session_id = response.get(
            "SessionId"
        )

        if not session_id:

            return jsonify({

                "success":
                    False,

                "error":
                    (
                        "Amazon Rekognition "
                        "did not return a SessionId."
                    )

            }), 500

        return jsonify({

            "success":
                True,

            "sessionId":
                session_id,

            "region":
                AWS_REGION

        }), 200

    except ClientError as error:

        message = (
            error.response
            .get("Error", {})
            .get(
                "Message",
                str(error)
            )
        )

        return jsonify({

            "success":
                False,

            "error":
                message

        }), 500

    except Exception as error:

        return jsonify({

            "success":
                False,

            "error":
                str(error)

        }), 500


# ============================================================
# MODULE 7 + 8
# FINAL LIVENESS RESULT
#
# THIS NOW DOES:
#
# Liveness
# -> ReferenceImage
# -> SearchFacesByImage
# -> Student lookup
# -> Attendance
# ============================================================

@app.route(
    "/api/liveness/result/<session_id>",
    methods=[
        "GET"
    ]
)
def get_liveness_result(
    session_id
):

    try:

        # ----------------------------------------------------
        # 1. GET LIVENESS RESULT
        # ----------------------------------------------------

        response = (
            rekognition
            .get_face_liveness_session_results(

                SessionId=(
                    session_id
                )
            )
        )

        status = response.get(
            "Status",
            "UNKNOWN"
        )

        confidence = response.get(
            "Confidence",
            0
        )

        audit_images = response.get(
            "AuditImages",
            []
        )

        reference_image = response.get(
            "ReferenceImage"
        )


        # ----------------------------------------------------
        # 2. CHECK LIVENESS
        # ----------------------------------------------------

        liveness_passed = (

            status
            ==
            "SUCCEEDED"

            and

            confidence
            >=
            LIVENESS_THRESHOLD
        )


        if not liveness_passed:

            return jsonify({

                "success":
                    True,

                "passed":
                    False,

                "identified":
                    False,

                "attendance_marked":
                    False,

                "sessionId":
                    session_id,

                "status":
                    status,

                "confidence":
                    confidence,

                "threshold":
                    LIVENESS_THRESHOLD,

                "message":
                    (
                        "Face liveness verification "
                        "did not pass."
                    )

            }), 200


        # ----------------------------------------------------
        # 3. GET REFERENCE IMAGE
        # ----------------------------------------------------

        if not reference_image:

            return jsonify({

                "success":
                    False,

                "passed":
                    True,

                "identified":
                    False,

                "attendance_marked":
                    False,

                "error":
                    (
                        "Liveness passed, but "
                        "Rekognition did not return "
                        "a reference image."
                    )

            }), 500


        reference_bytes = (
            reference_image.get(
                "Bytes"
            )
        )


        if not reference_bytes:

            return jsonify({

                "success":
                    False,

                "passed":
                    True,

                "identified":
                    False,

                "attendance_marked":
                    False,

                "error":
                    (
                        "Reference image bytes "
                        "are missing."
                    )

            }), 500


        # ----------------------------------------------------
        # 4. SEARCH REGISTERED STUDENTS
        # ----------------------------------------------------

        search_response = (
            rekognition
            .search_faces_by_image(

                CollectionId=(
                    STUDENT_COLLECTION
                ),

                Image={
                    "Bytes":
                        reference_bytes
                },

                FaceMatchThreshold=(
                    FACE_SEARCH_THRESHOLD
                ),

                MaxFaces=1
            )
        )


        matches = (
            search_response.get(
                "FaceMatches",
                []
            )
        )


        if not matches:

            return jsonify({

                "success":
                    True,

                "passed":
                    True,

                "identified":
                    False,

                "attendance_marked":
                    False,

                "sessionId":
                    session_id,

                "status":
                    status,

                "confidence":
                    confidence,

                "threshold":
                    LIVENESS_THRESHOLD,

                "message":
                    (
                        "Live person verified, "
                        "but no registered student "
                        "matched the face."
                    )

            }), 200


        # ----------------------------------------------------
        # 5. BEST MATCH
        # ----------------------------------------------------

        best_match = (
            matches[0]
        )

        similarity = (
            best_match.get(
                "Similarity",
                0
            )
        )

        matched_face = (
            best_match.get(
                "Face",
                {}
            )
        )

        student_id = (
            matched_face.get(
                "ExternalImageId"
            )
        )

        face_id = (
            matched_face.get(
                "FaceId"
            )
        )


        if not student_id:

            return jsonify({

                "success":
                    False,

                "passed":
                    True,

                "identified":
                    False,

                "attendance_marked":
                    False,

                "error":
                    (
                        "Matched Rekognition face "
                        "does not contain "
                        "ExternalImageId."
                    )

            }), 500


        # ----------------------------------------------------
        # 6. GET STUDENT DETAILS FROM DYNAMODB
        # ----------------------------------------------------

        student_response = (
            students_table
            .get_item(

                Key={
                    "student_id":
                        student_id
                }
            )
        )


        student = (
            student_response.get(
                "Item"
            )
        )


        if not student:

            return jsonify({

                "success":
                    False,

                "passed":
                    True,

                "identified":
                    True,

                "attendance_marked":
                    False,

                "student_id":
                    student_id,

                "error":
                    (
                        "Face matched, but student "
                        "metadata was not found "
                        "in VisionAI-Students."
                    )

            }), 404


        student_name = (
            student.get(
                "student_name",
                ""
            )
        )


        # ----------------------------------------------------
        # 7. DUPLICATE ATTENDANCE CHECK
        # ----------------------------------------------------

        now = datetime.now()

        today = now.strftime(
            "%Y-%m-%d"
        )


        attendance_scan = (
            attendance_table.scan()
        )

        existing_records = (
            attendance_scan.get(
                "Items",
                []
            )
        )


        already_present = any(

            item.get(
                "student_id"
            )
            ==
            student_id

            and

            item.get(
                "date"
            )
            ==
            today

            for item
            in existing_records
        )


        if already_present:

            return jsonify({

                "success":
                    True,

                "passed":
                    True,

                "identified":
                    True,

                "attendance_marked":
                    False,

                "already_present":
                    True,

                "sessionId":
                    session_id,

                "status":
                    status,

                "confidence":
                    confidence,

                "threshold":
                    LIVENESS_THRESHOLD,

                "similarity":
                    float(
                        similarity
                    ),

                "face_id":
                    face_id,

                "student": {

                    "student_id":
                        student_id,

                    "student_name":
                        student_name,

                    "email":
                        student.get(
                            "email",
                            ""
                        ),

                    "course":
                        student.get(
                            "course",
                            ""
                        )
                },

                "message":
                    (
                        "Attendance is already "
                        "marked for this student today."
                    )

            }), 200


        # ----------------------------------------------------
        # 8. CREATE ATTENDANCE RECORD
        # ----------------------------------------------------

        attendance_id = (

            student_id
            +
            "_"
            +
            now.strftime(
                "%Y%m%d_%H%M%S"
            )
            +
            "_"
            +
            str(
                uuid.uuid4()
            )[:8]
        )


        attendance_table.put_item(

            Item={

                "attendance_id":
                    attendance_id,

                "student_id":
                    student_id,

                "student_name":
                    student_name,

                "date":
                    today,

                "time":
                    now.strftime(
                        "%H:%M:%S"
                    ),

                "timestamp":
                    now.isoformat(),

                "similarity":
                    Decimal(
                        str(
                            round(
                                float(
                                    similarity
                                ),
                                2
                            )
                        )
                    ),

                "liveness_confidence":
                    Decimal(
                        str(
                            round(
                                float(
                                    confidence
                                ),
                                2
                            )
                        )
                    ),

                "status":
                    "PRESENT",

                "verification_method":
                    (
                        "FACE_LIVENESS_AND_"
                        "FACE_RECOGNITION"
                    ),

                "face_id":
                    face_id
                    or
                    ""
            }
        )


        # ----------------------------------------------------
        # 9. FINAL RESPONSE
        # ----------------------------------------------------

        return jsonify({

            "success":
                True,

            "passed":
                True,

            "identified":
                True,

            "attendance_marked":
                True,

            "already_present":
                False,

            "sessionId":
                session_id,

            "status":
                status,

            "confidence":
                confidence,

            "threshold":
                LIVENESS_THRESHOLD,

            "similarity":
                float(
                    similarity
                ),

            "face_id":
                face_id,

            "attendance_id":
                attendance_id,

            "auditImageCount":
                len(
                    audit_images
                ),

            "student": {

                "student_id":
                    student_id,

                "student_name":
                    student_name,

                "email":
                    student.get(
                        "email",
                        ""
                    ),

                "course":
                    student.get(
                        "course",
                        ""
                    )
            },

            "message":
                (
                    "Student verified and "
                    "attendance marked successfully."
                )

        }), 200


    except (
        rekognition
        .exceptions
        .InvalidParameterException
    ):

        return jsonify({

            "success":
                False,

            "passed":
                False,

            "identified":
                False,

            "attendance_marked":
                False,

            "error":
                (
                    "Amazon Rekognition could not "
                    "find a usable face in the "
                    "liveness reference image."
                )

        }), 400


    except ClientError as error:

        message = (
            error.response
            .get("Error", {})
            .get(
                "Message",
                str(error)
            )
        )

        return jsonify({

            "success":
                False,

            "passed":
                False,

            "identified":
                False,

            "attendance_marked":
                False,

            "error":
                message

        }), 500


    except Exception as error:

        return jsonify({

            "success":
                False,

            "passed":
                False,

            "identified":
                False,

            "attendance_marked":
                False,

            "error":
                str(error)

        }), 500


# ============================================================
# MODULE 8
# STUDENT REGISTRATION
# ============================================================

@app.route(
    "/smart-presence/register",
    methods=[
        "GET",
        "POST"
    ]
)
def smart_presence_register():

    if request.method == "GET":

        return render_template(
            "student_register.html"
        )

    student_id = (
        request.form
        .get(
            "student_id",
            ""
        )
        .strip()
    )

    student_name = (
        request.form
        .get(
            "student_name",
            ""
        )
        .strip()
    )

    email = (
        request.form
        .get(
            "email",
            ""
        )
        .strip()
    )

    course = (
        request.form
        .get(
            "course",
            ""
        )
        .strip()
    )

    image = request.files.get(
        "image"
    )


    if not student_id:

        return render_template(

            "student_register.html",

            error=(
                "Student ID is required."
            )
        )


    if not student_name:

        return render_template(

            "student_register.html",

            error=(
                "Student name is required."
            )
        )


    image_bytes, error = (
        validate_image(
            image
        )
    )


    if error:

        return render_template(

            "student_register.html",

            error=error,

            student_id=(
                student_id
            ),

            student_name=(
                student_name
            )
        )


    image_preview = create_preview(
        image_bytes,
        image.mimetype
    )


    try:

        # ----------------------------------------------------
        # CHECK EXISTING STUDENT
        # ----------------------------------------------------

        existing_student = (
            students_table
            .get_item(

                Key={
                    "student_id":
                        student_id
                }
            )
        )


        if existing_student.get(
            "Item"
        ):

            return render_template(

                "student_register.html",

                error=(
                    "Student ID already exists."
                ),

                image_preview=(
                    image_preview
                ),

                student_id=(
                    student_id
                ),

                student_name=(
                    student_name
                )
            )


        # ----------------------------------------------------
        # INDEX FACE INTO REKOGNITION
        # ----------------------------------------------------

        index_response = (
            rekognition
            .index_faces(

                CollectionId=(
                    STUDENT_COLLECTION
                ),

                Image={
                    "Bytes":
                        image_bytes
                },

                ExternalImageId=(
                    student_id
                ),

                MaxFaces=1,

                QualityFilter=(
                    "AUTO"
                ),

                DetectionAttributes=[
                    "DEFAULT"
                ]
            )
        )


        face_records = (
            index_response.get(
                "FaceRecords",
                []
            )
        )


        if not face_records:

            return render_template(

                "student_register.html",

                error=(
                    "No suitable face could "
                    "be registered. Use a clear "
                    "front-facing face image."
                ),

                image_preview=(
                    image_preview
                ),

                student_id=(
                    student_id
                ),

                student_name=(
                    student_name
                )
            )


        face = (
            face_records[0]
            .get(
                "Face",
                {}
            )
        )


        face_id = face.get(
            "FaceId"
        )


        if not face_id:

            return render_template(

                "student_register.html",

                image_preview=(
                    image_preview
                ),

                error=(
                    "Amazon Rekognition did not "
                    "return a FaceId."
                )
            )


        # ----------------------------------------------------
        # STORE STUDENT IN DYNAMODB
        # ----------------------------------------------------

        created_at = (
            datetime.now()
            .isoformat()
        )


        students_table.put_item(

            Item={

                "student_id":
                    student_id,

                "student_name":
                    student_name,

                "email":
                    email,

                "course":
                    course,

                "face_id":
                    face_id,

                "collection_id":
                    STUDENT_COLLECTION,

                "created_at":
                    created_at
            }
        )


        return render_template(

            "student_register.html",

            success=True,

            student_id=(
                student_id
            ),

            student_name=(
                student_name
            ),

            face_id=(
                face_id
            ),

            image_preview=(
                image_preview
            )
        )


    except ClientError as error:

        message = (
            error.response
            .get("Error", {})
            .get(
                "Message",
                str(error)
            )
        )

        return render_template(

            "student_register.html",

            image_preview=(
                image_preview
            ),

            error=(
                "AWS error: "
                +
                message
            )
        )


    except Exception as error:

        return render_template(

            "student_register.html",

            image_preview=(
                image_preview
            ),

            error=(
                "Application error: "
                +
                str(error)
            )
        )


# ============================================================
# MODULE 8
# MANUAL FACE IDENTIFICATION API
#
# Useful for testing with uploaded image.
# Final attendance uses liveness ReferenceImage automatically.
# ============================================================

@app.route(
    "/api/smart-presence/identify",
    methods=[
        "POST"
    ]
)
def identify_student():

    image = request.files.get(
        "image"
    )

    image_bytes, error = (
        validate_image(
            image
        )
    )

    if error:

        return jsonify({

            "success":
                False,

            "error":
                error

        }), 400


    try:

        response = (
            rekognition
            .search_faces_by_image(

                CollectionId=(
                    STUDENT_COLLECTION
                ),

                Image={
                    "Bytes":
                        image_bytes
                },

                FaceMatchThreshold=(
                    FACE_SEARCH_THRESHOLD
                ),

                MaxFaces=1
            )
        )


        matches = response.get(
            "FaceMatches",
            []
        )


        if not matches:

            return jsonify({

                "success":
                    True,

                "identified":
                    False,

                "message":
                    "Student not recognized."

            }), 200


        best_match = (
            matches[0]
        )

        matched_face = (
            best_match.get(
                "Face",
                {}
            )
        )

        similarity = (
            best_match.get(
                "Similarity",
                0
            )
        )

        student_id = (
            matched_face.get(
                "ExternalImageId"
            )
        )


        if not student_id:

            return jsonify({

                "success":
                    False,

                "error":
                    (
                        "Matched face has no "
                        "ExternalImageId."
                    )

            }), 500


        student_response = (
            students_table
            .get_item(

                Key={
                    "student_id":
                        student_id
                }
            )
        )


        student = (
            student_response.get(
                "Item"
            )
        )


        if not student:

            return jsonify({

                "success":
                    False,

                "error":
                    "Student metadata not found."

            }), 404


        return jsonify({

            "success":
                True,

            "identified":
                True,

            "similarity":
                float(
                    similarity
                ),

            "student": {

                "student_id":
                    student.get(
                        "student_id"
                    ),

                "student_name":
                    student.get(
                        "student_name"
                    ),

                "email":
                    student.get(
                        "email",
                        ""
                    ),

                "course":
                    student.get(
                        "course",
                        ""
                    )
            }

        }), 200


    except (
        rekognition
        .exceptions
        .InvalidParameterException
    ):

        return jsonify({

            "success":
                False,

            "error":
                "No usable face was detected."

        }), 400


    except Exception as error:

        return jsonify({

            "success":
                False,

            "error":
                str(error)

        }), 500


# ============================================================
# MODULE 8
# MANUAL ATTENDANCE API
#
# Retained for testing / future integrations.
# ============================================================

@app.route(
    "/api/smart-presence/attendance",
    methods=[
        "POST"
    ]
)
def record_attendance():

    data = (
        request.get_json(
            silent=True
        )
        or
        {}
    )

    student_id = data.get(
        "student_id"
    )

    student_name = data.get(
        "student_name",
        ""
    )

    similarity = data.get(
        "similarity",
        0
    )

    liveness_confidence = data.get(
        "liveness_confidence",
        0
    )


    if not student_id:

        return jsonify({

            "success":
                False,

            "error":
                "student_id is required."

        }), 400


    try:

        now = datetime.now()


        attendance_id = (

            student_id
            +
            "_"
            +
            now.strftime(
                "%Y%m%d_%H%M%S"
            )
            +
            "_"
            +
            str(
                uuid.uuid4()
            )[:8]
        )


        attendance_table.put_item(

            Item={

                "attendance_id":
                    attendance_id,

                "student_id":
                    student_id,

                "student_name":
                    student_name,

                "date":
                    now.strftime(
                        "%Y-%m-%d"
                    ),

                "time":
                    now.strftime(
                        "%H:%M:%S"
                    ),

                "timestamp":
                    now.isoformat(),

                "similarity":
                    Decimal(
                        str(
                            round(
                                float(
                                    similarity
                                ),
                                2
                            )
                        )
                    ),

                "liveness_confidence":
                    Decimal(
                        str(
                            round(
                                float(
                                    liveness_confidence
                                ),
                                2
                            )
                        )
                    ),

                "status":
                    "PRESENT"
            }
        )


        return jsonify({

            "success":
                True,

            "attendance_id":
                attendance_id,

            "message":
                (
                    "Attendance marked "
                    "successfully."
                )

        }), 200


    except Exception as error:

        return jsonify({

            "success":
                False,

            "error":
                str(error)

        }), 500


# ============================================================
# MODULE 8
# SMARTPRESENCE DASHBOARD
# ============================================================

@app.route(
    "/smart-presence"
)
def smart_presence():

    try:

        students_response = (
            students_table.scan()
        )

        attendance_response = (
            attendance_table.scan()
        )

        students = (
            students_response.get(
                "Items",
                []
            )
        )

        attendance = (
            attendance_response.get(
                "Items",
                []
            )
        )


        students = sorted(

            students,

            key=lambda item:
                item.get(
                    "student_id",
                    ""
                )
        )


        attendance = sorted(

            attendance,

            key=lambda item:
                item.get(
                    "timestamp",
                    ""
                ),

            reverse=True
        )


        today = (
            datetime.now()
            .strftime(
                "%Y-%m-%d"
            )
        )


        today_records = [

            item

            for item
            in attendance

            if item.get(
                "date"
            )
            ==
            today
        ]


        unique_students_today = {

            item.get(
                "student_id"
            )

            for item
            in today_records

            if item.get(
                "student_id"
            )
        }


        return render_template(

            "smart_presence.html",

            students=(
                students
            ),

            attendance=(
                attendance
            ),

            student_count=len(
                students
            ),

            total_attendance=len(
                attendance
            ),

            today_count=len(
                unique_students_today
            ),

            today=(
                today
            )
        )


    except Exception as error:

        return render_template(

            "smart_presence.html",

            students=[],

            attendance=[],

            student_count=0,

            total_attendance=0,

            today_count=0,

            today=(
                datetime.now()
                .strftime(
                    "%Y-%m-%d"
                )
            ),

            error=(
                str(error)
            )
        )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route(
    "/health"
)
def health():

    return jsonify({

        "status":
            "UP",

        "application":
            "VisionAI Pro",

        "region":
            AWS_REGION,

        "modules":
            8,

        "smart_presence": {

            "collection":
                STUDENT_COLLECTION,

            "students_table":
                STUDENTS_TABLE,

            "attendance_table":
                ATTENDANCE_TABLE,

            "liveness_threshold":
                LIVENESS_THRESHOLD,

            "face_search_threshold":
                FACE_SEARCH_THRESHOLD
        }

    }), 200


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=5000,

        debug=True
    )
