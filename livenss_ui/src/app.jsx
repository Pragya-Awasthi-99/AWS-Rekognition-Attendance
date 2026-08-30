import React, {
    useRef,
    useState
} from "react";

import {
    Amplify
} from "aws-amplify";

import {
    FaceLivenessDetector
} from "@aws-amplify/ui-react-liveness";

import {
    ThemeProvider
} from "@aws-amplify/ui-react";

import "@aws-amplify/ui-react/styles.css";


/*
============================================================
VISIONAI PRO
MODULE 7 + MODULE 8
LIVEVERIFY + SMARTPRESENCE
============================================================

.env

VITE_API_BASE_URL=https://visionai.reyazclouddevops.click

VITE_COGNITO_IDENTITY_POOL_ID=
ap-south-1:YOUR-REAL-IDENTITY-POOL-ID

============================================================
*/


const AWS_REGION =
    "ap-south-1";


const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL
    ||
    "https://visionai.reyazclouddevops.click";


const IDENTITY_POOL_ID =
    import.meta.env.VITE_COGNITO_IDENTITY_POOL_ID;


/*
============================================================
AMPLIFY CONFIGURATION
============================================================
*/

if (IDENTITY_POOL_ID) {

    Amplify.configure({

        Auth: {

            Cognito: {

                identityPoolId:
                    IDENTITY_POOL_ID,

                allowGuestAccess:
                    true
            }
        }
    });
}


/*
============================================================
MAIN APPLICATION
============================================================
*/

function App() {

    const [
        sessionId,
        setSessionId
    ] = useState(null);


    const [
        status,
        setStatus
    ] = useState(
        "READY"
    );


    const [
        result,
        setResult
    ] = useState(null);


    const [
        error,
        setError
    ] = useState(null);


    const [
        creatingSession,
        setCreatingSession
    ] = useState(false);


    const errorHandled =
        useRef(false);


    /*
    ========================================================
    RESET
    ========================================================
    */

    const resetVerification =
        () => {

            setSessionId(
                null
            );

            setResult(
                null
            );

            setError(
                null
            );

            setStatus(
                "READY"
            );

            setCreatingSession(
                false
            );

            errorHandled.current =
                false;
        };


    /*
    ========================================================
    CREATE NEW LIVENESS SESSION
    ========================================================
    */

    const createSession =
        async () => {

            if (!IDENTITY_POOL_ID) {

                setError(
                    "Cognito Identity Pool is not configured."
                );

                setStatus(
                    "ERROR"
                );

                return;
            }


            try {

                setCreatingSession(
                    true
                );

                setError(
                    null
                );

                setResult(
                    null
                );

                setSessionId(
                    null
                );

                setStatus(
                    "CREATING_SESSION"
                );


                console.log(
                    "Creating Face Liveness session..."
                );


                const response =
                    await fetch(

                        `${API_BASE_URL}/api/liveness/create-session`,

                        {
                            method:
                                "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            }
                        }
                    );


                const rawResponse =
                    await response.text();


                console.log(
                    "Create Session Raw Response:",
                    rawResponse
                );


                let data;


                try {

                    data =
                        JSON.parse(
                            rawResponse
                        );

                } catch {

                    throw new Error(
                        "Flask backend returned invalid JSON. " +
                        rawResponse.substring(
                            0,
                            250
                        )
                    );
                }


                if (!response.ok) {

                    throw new Error(
                        data?.error
                        ||
                        `Session API failed with HTTP ${response.status}`
                    );
                }


                if (!data?.success) {

                    throw new Error(
                        data?.error
                        ||
                        "Unable to create liveness session."
                    );
                }


                if (!data?.sessionId) {

                    throw new Error(
                        "No SessionId returned by backend."
                    );
                }


                if (
                    data?.region
                    &&
                    data.region
                    !==
                    AWS_REGION
                ) {

                    throw new Error(
                        `Region mismatch. Backend=${data.region}, Frontend=${AWS_REGION}`
                    );
                }


                console.log(
                    "New Liveness Session:",
                    data.sessionId
                );


                setSessionId(
                    data.sessionId
                );


                setStatus(
                    "CAMERA_READY"
                );


            } catch (err) {

                console.error(
                    "CREATE SESSION ERROR:",
                    err
                );


                setError(
                    extractErrorMessage(
                        err
                    )
                );


                setStatus(
                    "ERROR"
                );


            } finally {

                setCreatingSession(
                    false
                );
            }
        };


    /*
    ========================================================
    GET FINAL RESULT
    ========================================================

    Flask backend now performs:

    GetFaceLivenessSessionResults
        ↓
    ReferenceImage
        ↓
    SearchFacesByImage
        ↓
    Student lookup
        ↓
    Attendance write

    ========================================================
    */

    const getFinalResult =
        async () => {

            if (!sessionId) {

                throw new Error(
                    "Missing Face Liveness SessionId."
                );
            }


            setStatus(
                "PROCESSING"
            );


            console.log(
                "Retrieving SmartPresence result..."
            );


            const response =
                await fetch(

                    `${API_BASE_URL}/api/liveness/result/${encodeURIComponent(
                        sessionId
                    )}`,

                    {
                        method:
                            "GET",

                        headers: {
                            Accept:
                                "application/json"
                        }
                    }
                );


            const rawResponse =
                await response.text();


            console.log(
                "Final Result Raw Response:",
                rawResponse
            );


            let data;


            try {

                data =
                    JSON.parse(
                        rawResponse
                    );

            } catch {

                throw new Error(
                    "Flask backend returned invalid result JSON. " +
                    rawResponse.substring(
                        0,
                        250
                    )
                );
            }


            console.log(
                "SmartPresence Final Result:",
                data
            );


            if (!response.ok) {

                throw new Error(
                    data?.error
                    ||
                    `Result API failed with HTTP ${response.status}`
                );
            }


            if (!data?.success) {

                throw new Error(
                    data?.error
                    ||
                    "SmartPresence verification failed."
                );
            }


            setResult(
                data
            );


            setStatus(
                "COMPLETE"
            );
        };


    /*
    ========================================================
    AMPLIFY LIVENESS COMPLETE
    ========================================================
    */

    const handleAnalysisComplete =
        async () => {

            console.log(
                "Face Liveness challenge completed."
            );


            try {

                await getFinalResult();

            } catch (err) {

                console.error(
                    "FINAL RESULT ERROR:",
                    err
                );


                setError(
                    extractErrorMessage(
                        err
                    )
                );


                setStatus(
                    "ERROR"
                );
            }
        };


    /*
    ========================================================
    AMPLIFY ERROR
    ========================================================
    */

    const handleLivenessError =
        (err) => {

            if (
                errorHandled.current
            ) {

                return;
            }


            errorHandled.current =
                true;


            console.error(
                "======================================"
            );

            console.error(
                "VISIONAI LIVEVERIFY ERROR"
            );

            console.error(
                err
            );

            console.error(
                "Name:",
                err?.name
            );

            console.error(
                "Message:",
                err?.message
            );

            console.error(
                "State:",
                err?.state
            );

            console.error(
                "Nested Error:",
                err?.error
            );

            console.error(
                "======================================"
            );


            setError(
                extractErrorMessage(
                    err
                )
            );


            setStatus(
                "ERROR"
            );
        };


    /*
    ========================================================
    UI
    ========================================================
    */

    return (

        <ThemeProvider>


        <div
            style={{
                minHeight:
                    "100vh",

                background:
                    "linear-gradient(180deg,#f4f7fc 0%,#edf2f9 100%)",

                fontFamily:
                    '"Segoe UI", Arial, sans-serif',

                color:
                    "#172033"
            }}
        >


            {/* =========================================
                NAVBAR
            ========================================= */}


            <header
                style={{
                    display:
                        "flex",

                    justifyContent:
                        "space-between",

                    alignItems:
                        "center",

                    padding:
                        "17px 5%",

                    background:
                        "linear-gradient(120deg,#06152e,#102a56)",

                    color:
                        "white",

                    boxShadow:
                        "0 8px 30px rgba(0,0,0,.18)"
                }}
            >


                <div
                    style={{
                        display:
                            "flex",

                        alignItems:
                            "center",

                        gap:
                            "12px"
                    }}
                >


                    <div
                        style={{
                            width:
                                "50px",

                            height:
                                "50px",

                            borderRadius:
                                "15px",

                            display:
                                "flex",

                            justifyContent:
                                "center",

                            alignItems:
                                "center",

                            fontSize:
                                "26px",

                            background:
                                "linear-gradient(135deg,#4778ff,#923cff)"
                        }}
                    >

                        🧠

                    </div>


                    <div>

                        <h2
                            style={{
                                margin:
                                    0
                            }}
                        >

                            VisionAI Pro

                        </h2>


                        <small
                            style={{
                                color:
                                    "#b8cae9"
                            }}
                        >

                            SmartPresence AI

                        </small>

                    </div>


                </div>


                <div
                    style={{
                        padding:
                            "10px 18px",

                        border:
                            "1px solid rgba(255,255,255,.2)",

                        borderRadius:
                            "12px",

                        background:
                            "rgba(255,255,255,.06)",

                        textAlign:
                            "center"
                    }}
                >

                    <strong
                        style={{
                            display:
                                "block"
                        }}
                    >

                        AWS

                    </strong>


                    <span
                        style={{
                            color:
                                "#ffb44c",

                            fontSize:
                                "12px"
                        }}
                    >

                        Rekognition + DynamoDB

                    </span>

                </div>


            </header>



            {/* =========================================
                HERO
            ========================================= */}


            <section
                style={{
                    padding:
                        "55px 5% 95px",

                    color:
                        "white",

                    background:
                        "radial-gradient(circle at 84% 30%,rgba(80,120,255,.38),transparent 30%),linear-gradient(120deg,#06152e,#0b2d5c)"
                }}
            >


                <div
                    style={{
                        maxWidth:
                            "1450px",

                        margin:
                            "auto"
                    }}
                >


                    <div
                        style={{
                            display:
                                "inline-block",

                            padding:
                                "8px 14px",

                            borderRadius:
                                "30px",

                            background:
                                "rgba(255,255,255,.08)",

                            border:
                                "1px solid rgba(255,255,255,.12)",

                            fontSize:
                                "13px",

                            marginBottom:
                                "15px"
                        }}
                    >

                        🛡 SmartPresence Verification Engine

                    </div>


                    <h1
                        style={{
                            margin:
                                "0 0 14px",

                            fontSize:
                                "clamp(38px,4vw,60px)"
                        }}
                    >

                        Live Identity
                        {" "}

                        <span
                            style={{
                                color:
                                    "#85aaff"
                            }}
                        >

                            Attendance

                        </span>

                    </h1>


                    <p
                        style={{
                            maxWidth:
                                "850px",

                            color:
                                "#c9d7ed",

                            fontSize:
                                "17px",

                            lineHeight:
                                1.7
                        }}
                    >

                        Complete Face Liveness verification.
                        VisionAI will automatically identify
                        the registered student and mark
                        attendance if both liveness and
                        face recognition succeed.

                    </p>


                </div>


            </section>



            {/* =========================================
                MAIN
            ========================================= */}


            <main
                style={{
                    width:
                        "94%",

                    maxWidth:
                        "1200px",

                    margin:
                        "-45px auto 60px"
                }}
            >


                <div
                    style={{
                        background:
                            "white",

                        padding:
                            "28px",

                        borderRadius:
                            "22px",

                        boxShadow:
                            "0 12px 40px rgba(31,56,97,.12)"
                    }}
                >


                    {/* =================================
                        READY
                    ================================= */}


                    {
                        status ===
                        "READY"
                        &&
                        (

                            <div
                                style={{
                                    textAlign:
                                        "center"
                                }}
                            >


                                <div
                                    style={{
                                        fontSize:
                                            "72px"
                                    }}
                                >

                                    🛡️

                                </div>


                                <h2>

                                    SmartPresence Ready

                                </h2>


                                <p
                                    style={{
                                        maxWidth:
                                            "700px",

                                        margin:
                                            "10px auto 26px",

                                        color:
                                            "#68758b",

                                        lineHeight:
                                            1.7
                                    }}
                                >

                                    Look into the camera and complete
                                    the Face Liveness challenge.
                                    VisionAI will then search the
                                    registered student collection and
                                    automatically mark attendance.

                                </p>


                                <div
                                    style={{
                                        display:
                                            "grid",

                                        gridTemplateColumns:
                                            "repeat(auto-fit,minmax(170px,1fr))",

                                        gap:
                                            "12px",

                                        maxWidth:
                                            "800px",

                                        margin:
                                            "0 auto 28px"
                                    }}
                                >


                                    <InfoCard

                                        icon="📷"

                                        title="Live Camera"

                                        text="Camera-based verification"

                                    />


                                    <InfoCard

                                        icon="🛡️"

                                        title="Liveness"

                                        text="Verify real human presence"

                                    />


                                    <InfoCard

                                        icon="🔍"

                                        title="Recognition"

                                        text="Match registered student"

                                    />


                                    <InfoCard

                                        icon="📝"

                                        title="Attendance"

                                        text="Mark automatically"

                                    />


                                </div>


                                <button

                                    onClick={
                                        createSession
                                    }

                                    disabled={
                                        creatingSession
                                        ||
                                        !IDENTITY_POOL_ID
                                    }

                                    style={
                                        primaryButtonStyle
                                    }
                                >

                                    {
                                        creatingSession
                                        ?
                                        "Creating Secure Session..."
                                        :
                                        "🛡 Start Smart Attendance"
                                    }

                                </button>


                            </div>
                        )
                    }



                    {/* =================================
                        CREATING SESSION
                    ================================= */}


                    {
                        status ===
                        "CREATING_SESSION"
                        &&
                        (

                            <StatusMessage

                                icon="⏳"

                                title="Creating Secure Session"

                                text="Connecting to Amazon Rekognition Face Liveness..."

                            />
                        )
                    }



                    {/* =================================
                        CAMERA
                    ================================= */}


                    {
                        sessionId
                        &&
                        status ===
                        "CAMERA_READY"
                        &&
                        (

                            <div>


                                <div
                                    style={{
                                        padding:
                                            "14px",

                                        marginBottom:
                                            "18px",

                                        borderRadius:
                                            "12px",

                                        background:
                                            "#edf6ff",

                                        color:
                                            "#315f9c"
                                    }}
                                >

                                    <strong>
                                        📷 Secure session ready
                                    </strong>

                                    <br />

                                    Session:
                                    {" "}

                                    <code>

                                        {
                                            sessionId.slice(
                                                0,
                                                12
                                            )
                                        }
                                        ...

                                    </code>

                                    <br />

                                    Region:
                                    {" "}

                                    <strong>

                                        {
                                            AWS_REGION
                                        }

                                    </strong>

                                </div>


                                <FaceLivenessDetector

                                    sessionId={
                                        sessionId
                                    }

                                    region={
                                        AWS_REGION
                                    }

                                    onAnalysisComplete={
                                        handleAnalysisComplete
                                    }

                                    onError={
                                        handleLivenessError
                                    }

                                />


                            </div>
                        )
                    }



                    {/* =================================
                        PROCESSING FINAL RESULT
                    ================================= */}


                    {
                        status ===
                        "PROCESSING"
                        &&
                        (

                            <StatusMessage

                                icon="🤖"

                                title="Identifying Student"

                                text="Liveness passed. VisionAI is now searching the registered face collection and recording attendance..."

                            />
                        )
                    }



                    {/* =================================
                        COMPLETE
                    ================================= */}


                    {
                        status ===
                        "COMPLETE"
                        &&
                        result
                        &&
                        (

                            <FinalResult

                                result={
                                    result
                                }

                                resetVerification={
                                    resetVerification
                                }

                                API_BASE_URL={
                                    API_BASE_URL
                                }

                            />
                        )
                    }



                    {/* =================================
                        ERROR
                    ================================= */}


                    {
                        status ===
                        "ERROR"
                        &&
                        (

                            <div
                                style={{
                                    textAlign:
                                        "center"
                                }}
                            >


                                <div
                                    style={{
                                        fontSize:
                                            "64px"
                                    }}
                                >

                                    ⚠️

                                </div>


                                <h2
                                    style={{
                                        color:
                                            "#b53333"
                                    }}
                                >

                                    SmartPresence Error

                                </h2>


                                <div
                                    style={{
                                        maxWidth:
                                            "850px",

                                        margin:
                                            "15px auto 25px",

                                        padding:
                                            "18px",

                                        borderRadius:
                                            "12px",

                                        background:
                                            "#fff0f0",

                                        color:
                                            "#9c2d2d",

                                        overflowWrap:
                                            "anywhere"
                                    }}
                                >

                                    {
                                        error
                                        ||
                                        "Unknown verification error."
                                    }

                                </div>


                                <button

                                    onClick={
                                        resetVerification
                                    }

                                    style={
                                        primaryButtonStyle
                                    }
                                >

                                    ↻ Try Again

                                </button>


                            </div>
                        )
                    }


                </div>


                {/* =====================================
                    BOTTOM LINKS
                ===================================== */}


                <div
                    style={{
                        marginTop:
                            "20px",

                        display:
                            "flex",

                        flexWrap:
                            "wrap",

                        gap:
                            "12px"
                    }}
                >


                    <a
                        href={
                            `${API_BASE_URL}/smart-presence`
                        }

                        style={
                            linkButtonStyle
                        }
                    >

                        📊 SmartPresence Dashboard

                    </a>


                    <a
                        href={
                            `${API_BASE_URL}/smart-presence/register`
                        }

                        style={
                            linkButtonStyle
                        }
                    >

                        👤 Register Student

                    </a>


                    <a
                        href={
                            `${API_BASE_URL}/`
                        }

                        style={
                            linkButtonStyle
                        }
                    >

                        ← VisionAI Dashboard

                    </a>


                </div>


            </main>


        </div>


        </ThemeProvider>
    );
}


/*
============================================================
FINAL RESULT COMPONENT
============================================================
*/

function FinalResult({
    result,
    resetVerification,
    API_BASE_URL
}) {

    /*
    ========================================================
    CASE 1
    LIVENESS FAILED
    ========================================================
    */

    if (
        !result.passed
    ) {

        return (

            <ResultMessage

                icon="❌"

                title="Liveness Verification Failed"

                color="#b53333"

                text={
                    result.message
                    ||
                    "Face liveness verification did not pass."
                }

                buttonText="Try Again"

                onClick={
                    resetVerification
                }

            />
        );
    }


    /*
    ========================================================
    CASE 2
    LIVE PERSON BUT NOT REGISTERED
    ========================================================
    */

    if (
        result.passed
        &&
        !result.identified
    ) {

        return (

            <div
                style={{
                    textAlign:
                        "center"
                }}
            >


                <div
                    style={{
                        fontSize:
                            "72px"
                    }}
                >

                    👤

                </div>


                <h2
                    style={{
                        color:
                            "#c27a12"
                    }}
                >

                    Live Person Verified

                </h2>


                <h3>

                    Student Not Recognized

                </h3>


                <p
                    style={{
                        color:
                            "#68758b",

                        lineHeight:
                            1.7
                    }}
                >

                    {
                        result.message
                        ||
                        "The person passed Face Liveness, but no registered student matched the face."
                    }

                </p>


                <ResultGrid>


                    <ResultCard

                        label="Liveness"

                        value={
                            `${Number(
                                result.confidence
                                ||
                                0
                            ).toFixed(2)}%`
                        }

                    />


                    <ResultCard

                        label="Recognition"

                        value="NO MATCH"

                    />


                </ResultGrid>


                <button

                    onClick={
                        resetVerification
                    }

                    style={
                        primaryButtonStyle
                    }
                >

                    ↻ Try Again

                </button>


                <a

                    href={
                        `${API_BASE_URL}/smart-presence/register`
                    }

                    style={{
                        ...secondaryButtonStyle,
                        marginLeft:
                            "10px"
                    }}
                >

                    Register Student

                </a>


            </div>
        );
    }


    /*
    ========================================================
    CASE 3
    STUDENT ALREADY PRESENT TODAY
    ========================================================
    */

    if (
        result.identified
        &&
        result.already_present
    ) {

        return (

            <div
                style={{
                    textAlign:
                        "center"
                }}
            >


                <div
                    style={{
                        fontSize:
                            "72px"
                    }}
                >

                    ℹ️

                </div>


                <h2
                    style={{
                        color:
                            "#315f9c"
                    }}
                >

                    Attendance Already Marked

                </h2>


                <h1>

                    Welcome,
                    {" "}

                    {
                        result.student
                        ?.student_name
                    }

                </h1>


                <p
                    style={{
                        color:
                            "#68758b"
                    }}
                >

                    Your attendance has already
                    been recorded for today.

                </p>


                <StudentResultDetails

                    result={
                        result
                    }

                />


                <button

                    onClick={
                        resetVerification
                    }

                    style={
                        primaryButtonStyle
                    }
                >

                    Verify Another Student

                </button>


                <a

                    href={
                        `${API_BASE_URL}/smart-presence`
                    }

                    style={{
                        ...secondaryButtonStyle,
                        marginLeft:
                            "10px"
                    }}
                >

                    Attendance Dashboard

                </a>


            </div>
        );
    }


    /*
    ========================================================
    CASE 4
    ATTENDANCE SUCCESS
    ========================================================
    */

    return (

        <div
            style={{
                textAlign:
                    "center"
            }}
        >


            <div
                style={{
                    fontSize:
                        "80px"
                }}
            >

                ✅

            </div>


            <h2
                style={{
                    color:
                        "#168348",

                    marginBottom:
                        "8px"
                }}
            >

                Attendance Marked Successfully

            </h2>


            <h1
                style={{
                    margin:
                        "8px 0"
                }}
            >

                Welcome,
                {" "}

                {
                    result.student
                    ?.student_name
                    ||
                    "Student"
                }

            </h1>


            <p
                style={{
                    color:
                        "#68758b",

                    fontSize:
                        "15px"
                }}
            >

                Identity and live presence
                were successfully verified.

            </p>


            <StudentResultDetails

                result={
                    result
                }

            />


            <div
                style={{
                    margin:
                        "22px 0",

                    padding:
                        "16px",

                    borderRadius:
                        "13px",

                    background:
                        "#eaf9ef",

                    color:
                        "#176737",

                    textAlign:
                        "left"
                }}
            >

                <strong>
                    ✅ SmartPresence Complete
                </strong>

                <br /><br />

                Live person verified
                → Face recognized
                → Student identified
                → Attendance stored in DynamoDB.

            </div>


            <button

                onClick={
                    resetVerification
                }

                style={
                    primaryButtonStyle
                }
            >

                👤 Verify Next Student

            </button>


            <a

                href={
                    `${API_BASE_URL}/smart-presence`
                }

                style={{
                    ...secondaryButtonStyle,
                    marginLeft:
                        "10px"
                }}
            >

                📊 View Attendance Dashboard

            </a>


        </div>
    );
}


/*
============================================================
STUDENT RESULT DETAILS
============================================================
*/

function StudentResultDetails({
    result
}) {

    const student =
        result.student
        ||
        {};


    return (

        <>


        <ResultGrid>


            <ResultCard

                label="Student ID"

                value={
                    student.student_id
                    ||
                    "-"
                }

            />


            <ResultCard

                label="Student Name"

                value={
                    student.student_name
                    ||
                    "-"
                }

            />


            <ResultCard

                label="Course"

                value={
                    student.course
                    ||
                    "-"
                }

            />


            <ResultCard

                label="Status"

                value={
                    result.attendance_marked
                    ?
                    "PRESENT"
                    :
                    result.already_present
                    ?
                    "ALREADY PRESENT"
                    :
                    "-"
                }

            />


        </ResultGrid>


        <ResultGrid>


            <ResultCard

                label="Liveness Confidence"

                value={
                    `${Number(
                        result.confidence
                        ||
                        0
                    ).toFixed(2)}%`
                }

            />


            <ResultCard

                label="Face Similarity"

                value={
                    `${Number(
                        result.similarity
                        ||
                        0
                    ).toFixed(2)}%`
                }

            />


            <ResultCard

                label="Face ID"

                value={
                    result.face_id
                    ?
                    `${result.face_id.slice(
                        0,
                        12
                    )}...`
                    :
                    "-"
                }

            />


            <ResultCard

                label="Verification"

                value="LIVENESS + FACE"

            />


        </ResultGrid>


        </>

    );
}


/*
============================================================
HELPERS
============================================================
*/

function extractErrorMessage(
    err
) {

    if (!err) {

        return (
            "Verification failed without an error object."
        );
    }


    const candidates = [

        err?.message,

        err?.error?.message,

        err?.cause?.message,

        err?.error,

        err?.state,

        err?.name
    ];


    for (
        const candidate
        of candidates
    ) {

        if (
            typeof candidate
            ===
            "string"

            &&

            candidate.trim()
        ) {

            return candidate;
        }
    }


    try {

        return JSON.stringify(
            err
        );

    } catch {

        return (
            "Verification failed. Check browser console."
        );
    }
}


/*
============================================================
REUSABLE COMPONENTS
============================================================
*/

function InfoCard({
    icon,
    title,
    text
}) {

    return (

        <div
            style={{
                padding:
                    "16px",

                border:
                    "1px solid #e4e9f2",

                borderRadius:
                    "14px",

                background:
                    "#f7f9fd"
            }}
        >


            <div
                style={{
                    fontSize:
                        "28px"
                }}
            >

                {
                    icon
                }

            </div>


            <strong>

                {
                    title
                }

            </strong>


            <div
                style={{
                    color:
                        "#738096",

                    fontSize:
                        "12px",

                    marginTop:
                        "5px"
                }}
            >

                {
                    text
                }

            </div>


        </div>
    );
}


function ResultGrid({
    children
}) {

    return (

        <div
            style={{
                display:
                    "grid",

                gridTemplateColumns:
                    "repeat(auto-fit,minmax(190px,1fr))",

                gap:
                    "14px",

                margin:
                    "25px 0"
            }}
        >

            {
                children
            }

        </div>
    );
}


function ResultCard({
    label,
    value
}) {

    return (

        <div
            style={{
                padding:
                    "18px",

                borderRadius:
                    "14px",

                background:
                    "#f7f9fd",

                border:
                    "1px solid #e4e9f2"
            }}
        >


            <div
                style={{
                    color:
                        "#758095",

                    fontSize:
                        "11px",

                    textTransform:
                        "uppercase",

                    marginBottom:
                        "8px"
                }}
            >

                {
                    label
                }

            </div>


            <div
                style={{
                    fontSize:
                        "20px",

                    fontWeight:
                        800,

                    color:
                        "#203b68",

                    overflowWrap:
                        "anywhere"
                }}
            >

                {
                    value
                }

            </div>


        </div>
    );
}


function StatusMessage({
    icon,
    title,
    text
}) {

    return (

        <div
            style={{
                textAlign:
                    "center",

                padding:
                    "55px 20px"
            }}
        >


            <div
                style={{
                    fontSize:
                        "62px"
                }}
            >

                {
                    icon
                }

            </div>


            <h2>

                {
                    title
                }

            </h2>


            <p
                style={{
                    maxWidth:
                        "680px",

                    margin:
                        "10px auto",

                    color:
                        "#6f7c91",

                    lineHeight:
                        1.6
                }}
            >

                {
                    text
                }

            </p>


        </div>
    );
}


function ResultMessage({
    icon,
    title,
    color,
    text,
    buttonText,
    onClick
}) {

    return (

        <div
            style={{
                textAlign:
                    "center"
            }}
        >


            <div
                style={{
                    fontSize:
                        "72px"
                }}
            >

                {
                    icon
                }

            </div>


            <h2
                style={{
                    color:
                        color
                }}
            >

                {
                    title
                }

            </h2>


            <p
                style={{
                    color:
                        "#68758b",

                    lineHeight:
                        1.7
                }}
            >

                {
                    text
                }

            </p>


            <button

                onClick={
                    onClick
                }

                style={
                    primaryButtonStyle
                }
            >

                {
                    buttonText
                }

            </button>


        </div>
    );
}


/*
============================================================
BUTTON STYLES
============================================================
*/

const primaryButtonStyle = {

    border:
        "none",

    borderRadius:
        "12px",

    padding:
        "14px 26px",

    fontSize:
        "15px",

    fontWeight:
        700,

    cursor:
        "pointer",

    color:
        "white",

    background:
        "linear-gradient(90deg,#4778ff,#823cff)",

    boxShadow:
        "0 8px 22px rgba(74,87,230,.22)"
};


const secondaryButtonStyle = {

    display:
        "inline-block",

    padding:
        "13px 20px",

    borderRadius:
        "11px",

    textDecoration:
        "none",

    fontWeight:
        700,

    color:
        "#425bc6",

    background:
        "#edf2ff"
};


const linkButtonStyle = {

    display:
        "inline-block",

    padding:
        "11px 16px",

    borderRadius:
        "10px",

    textDecoration:
        "none",

    fontWeight:
        700,

    color:
        "#425bc6",

    background:
        "#edf2ff",

    fontSize:
        "13px"
};


export default App;